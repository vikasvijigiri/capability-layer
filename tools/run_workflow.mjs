#!/usr/bin/env node

/**
 * Repository-owned workflow runner.
 *
 * Host-managed mode is the normal IDE-agent path: Claude Code, Codex, Gemini,
 * or VS Code executes the stages using the repository contract. Dry-run is
 * deterministic and requires no network, SDK, or credentials. SDK-live is an
 * optional standalone automation path. The runner owns state, approvals, and
 * schema-facing prompts; the workflow owns lifecycle order.
 */

import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const WORKFLOW_DIR = resolve(ROOT, '.claude', 'workflows')
const STATE_DIR = resolve(ROOT, '.claude', 'workflow-state')

function parseArgs(argv) {
  const result = { flags: new Set(), values: {} }
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i]
    if (!item.startsWith('--')) continue
    const [key, inline] = item.slice(2).split('=', 2)
    if (inline !== undefined) result.values[key] = inline
    else if (argv[i + 1] && !argv[i + 1].startsWith('--')) result.values[key] = argv[++i]
    else result.flags.add(key)
  }
  return result
}

function scrub(value) {
  if (typeof value === 'string') {
    return value
      .replace(/sk-[A-Za-z0-9_-]{12,}/g, '[REDACTED]')
      .replace(/AKIA[A-Z0-9]{16}/g, '[REDACTED]')
  }
  if (Array.isArray(value)) return value.map(scrub)
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, scrub(v)]))
  }
  return value
}

async function saveState(runId, state) {
  const path = resolve(STATE_DIR, `${runId}.json`)
  await mkdir(dirname(path), { recursive: true })
  const temporary = `${path}.${process.pid}.tmp`
  await writeFile(temporary, `${JSON.stringify(scrub(state), null, 2)}\n`, 'utf8')
  await rename(temporary, path)
  return path
}

function schemaInstruction(schema) {
  return `Return only valid JSON matching this schema; do not wrap it in markdown:\n${JSON.stringify(schema)}`
}

function mockResult(label) {
  if (label === 'frame') return {
    goal: 'Complete the bounded requested change.',
    constraints: ['Stay within the declared scope.'],
    doneCheck: ['Acceptance criteria are verified.'],
    outOfScope: ['Unrequested refactors.'],
  }
  if (label === 'plan') return {
    steps: ['Implement the smallest change.', 'Run the declared checks.'],
    validation: ['Run the project verification command.'],
    risks: [],
    rollback: 'Restore the changed files from the recorded branch state.',
  }
  if (label === 'implement') return {
    changedFiles: [],
    testsRun: ['dry-run: no repository edits performed'],
    risks: [],
    incomplete: [],
  }
  if (label === 'verification' || label === 'security') return {
    passed: true,
    findings: [],
    missingEvidence: ['Live execution is required before production use.'],
  }
  if (label === 'review') return { passed: true, findings: [], evidence: ['dry-run: review contract exercised'], scopeVerdict: 'clean' }
  if (label === 'integration') return { status: 'clean', conflictFiles: [], evidence: ['dry-run: merge queue handoff exercised'] }
  if (label === 'release-readiness') return {
    ready: true,
    blockingFindings: [],
    rollback: 'Host-managed rollback procedure required before production.',
    smoke: ['dry-run: release candidate checks represented'],
  }
  if (label === 'diagnose') return { category: 'repair', rootCause: 'dry-run injected failure is deterministic', evidence: ['dry-run diagnostic contract'], action: 'apply bounded repair' }
  if (label === 'repair') return { complete: true, changedFiles: [], evidence: ['dry-run repair contract'] }
  if (label === 'reverify') return { passed: true, evidence: ['dry-run re-verification contract'], findings: [] }
  if (label === 'release') return { deployed: false, rolledBack: false, stable: true, evidence: ['dry-run: no release side effect'], rollback: 'No release was performed.' }
  return null
}

function toolsFor(label) {
  if (label === 'implement') return ['Read', 'Edit', 'Bash', 'Glob', 'Grep']
  if (label === 'verification') return ['Read', 'Bash', 'Glob', 'Grep']
  return ['Read', 'Glob', 'Grep']
}

async function createLiveAgent(root, events) {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error('Live mode requires ANTHROPIC_API_KEY; use --dry-run for offline verification.')
  }
  let sdk
  try {
    sdk = await import('@anthropic-ai/claude-agent-sdk')
  } catch (error) {
    throw new Error('Live mode requires @anthropic-ai/claude-agent-sdk. Run npm install first.', { cause: error })
  }
  if (typeof sdk.query !== 'function') throw new Error('Installed Claude Agent SDK does not expose query().')

  return async function liveAgent(prompt, options = {}) {
    const label = options.label ?? 'agent'
    events.push({ type: 'stage-start', label, at: new Date().toISOString() })
    const enriched = `${prompt}\n\n${schemaInstruction(options.schema ?? { type: 'object' })}`
    const response = sdk.query({
      prompt: enriched,
      options: {
        cwd: root,
        settingSources: ['project'],
        allowedTools: toolsFor(label),
        permissionMode: label === 'implement' ? 'acceptEdits' : 'default',
      },
    })
    const chunks = []
    for await (const message of response) {
      if (message?.type === 'assistant') {
        const content = message.message?.content ?? message.content ?? []
        for (const block of content) if (block?.type === 'text') chunks.push(block.text)
      }
    }
    const text = chunks.join('\n').trim()
    const candidate = text.match(/\{[\s\S]*\}/)?.[0]
    if (!candidate) throw new Error(`${label} returned no JSON object.`)
    const result = JSON.parse(candidate)
    events.push({ type: 'stage-complete', label, at: new Date().toISOString() })
    return result
  }
}

function createDryAgent(events) {
  return async function dryAgent(_prompt, options = {}) {
    const label = options.label ?? 'agent'
    events.push({ type: 'stage-start', label, mode: 'dry-run', at: new Date().toISOString() })
    const result = mockResult(label)
    events.push({ type: 'stage-complete', label, mode: 'dry-run', at: new Date().toISOString() })
    return result
  }
}

function hostManagedResult(workflowName, input, runId) {
  return {
    status: 'awaiting-host-execution',
    mode: 'host-managed',
    runId,
    workflow: workflowName,
    input,
    contract: {
      instructionFile: 'AGENTS.md',
      workflowPolicy: '.claude/workflow.md',
      skills: '.claude/skills',
      agents: '.claude/agents',
      evidenceRequired: true,
      approvalsRequired: ['plan', 'shipment'],
      hostMayBe: ['Claude Code', 'Codex', 'Gemini', 'VS Code agent'],
    },
    next: 'Execute the workflow in the IDE agent host, then record evidence and rerun verification.',
  }
}

async function execute(workflowName, parsed) {
  const hostManaged = parsed.flags.has('host-managed') || parsed.flags.has('ide-agent')
  const sdkLive = parsed.flags.has('sdk-live') || parsed.flags.has('live')
  const dryRun = !hostManaged && !sdkLive
  const runId = parsed.values['run-id'] ?? `${workflowName}-${Date.now()}`
  const events = []
  const input = {
    task: parsed.values.task ?? parsed.values.request,
    scope: parsed.values.scope,
    acceptance: parsed.values.acceptance,
    planApproved: parsed.flags.has('plan-approved'),
    releaseApproved: parsed.flags.has('release-approved'),
    shipmentApproved: parsed.flags.has('shipment-approved') || parsed.flags.has('release-approved'),
  }
  if (hostManaged) {
    const result = hostManagedResult(workflowName, input, runId)
    const state = {
      runId,
      workflow: workflowName,
      mode: 'host-managed',
      status: result.status,
      input,
      events: [{ type: 'host-handoff', at: new Date().toISOString() }],
      result,
      updatedAt: new Date().toISOString(),
    }
    const statePath = await saveState(runId, state)
    return { ...result, statePath }
  }
  const module = await import(pathToFileURL(resolve(WORKFLOW_DIR, `${workflowName}.js`)))
  if (typeof module.run !== 'function') throw new Error(`${workflowName} must export run({ args, agent, pipeline }).`)
  const agent = dryRun ? createDryAgent(events) : await createLiveAgent(ROOT, events)
  const pipeline = async (items, callback) => {
    const results = new Array(items.length)
    const concurrency = 2
    for (let start = 0; start < items.length; start += concurrency) {
      const batch = items.slice(start, start + concurrency)
      const values = await Promise.all(batch.map((item, offset) => callback(item, start + offset)))
      values.forEach((value, offset) => { results[start + offset] = value })
    }
    return results
  }
  const result = await module.run({ args: input, agent, pipeline })
  const state = {
    runId,
    workflow: workflowName,
    mode: dryRun ? 'dry-run' : 'live',
    status: result?.status ?? 'unknown',
    input,
    events,
    result,
    updatedAt: new Date().toISOString(),
  }
  const statePath = await saveState(runId, state)
  return { ...result, runId, statePath, mode: state.mode }
}

function usage() {
  console.log('Usage: node tools/run_workflow.mjs <workflow> [--dry-run|--host-managed|--sdk-live] --task <text> [--scope <text>] [--acceptance <text>] [--plan-approved] [--shipment-approved]')
}

const parsed = parseArgs(process.argv.slice(2))
const workflowName = process.argv[2]?.startsWith('--') ? null : process.argv[2]
if (!workflowName || parsed.flags.has('help')) {
  usage()
  process.exit(workflowName ? 0 : 2)
}

try {
  const result = await execute(workflowName, parsed)
  console.log(JSON.stringify(result, null, 2))
  process.exit(result.status === 'blocked' ? 2 : 0)
} catch (error) {
  console.error(`workflow failed: ${error.message}`)
  process.exit(1)
}
