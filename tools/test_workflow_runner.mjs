#!/usr/bin/env node

import { spawnSync } from 'node:child_process'
import { readFile, rm } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const runner = fileURLToPath(new URL('./run_workflow.mjs', import.meta.url))
const root = fileURLToPath(new URL('..', import.meta.url))
const runId = `runner-test-${process.pid}`
const hostRunId = `host-runner-test-${process.pid}`

function invoke(...args) {
  const result = spawnSync(process.execPath, [runner, 'feature-delivery', '--dry-run', '--run-id', runId, ...args], {
    cwd: root,
    encoding: 'utf8',
  })
  if (result.status !== 0 && result.status !== 2) throw new Error(result.stderr)
  return JSON.parse(result.stdout)
}

function invokeHost(...args) {
  const result = spawnSync(process.execPath, [runner, 'feature-delivery', '--host-managed', '--run-id', hostRunId, ...args], {
    cwd: root,
    encoding: 'utf8',
  })
  if (result.status !== 0) throw new Error(result.stderr)
  return JSON.parse(result.stdout)
}

try {
  const planned = invoke('--task', 'test runner', '--scope', 'fixtures', '--acceptance', 'dry-run works')
  if (planned.status !== 'awaiting-plan-approval') throw new Error(`unexpected plan status: ${planned.status}`)

  const reviewed = invoke('--task', 'test runner', '--scope', 'fixtures', '--acceptance', 'dry-run works', '--plan-approved')
  if (reviewed.status !== 'awaiting-ship-approval') throw new Error(`unexpected review status: ${reviewed.status}`)

  const blocked = invoke('--task', 'test runner', '--scope', 'fixtures', '--acceptance', 'dry-run works', '--plan-approved', '--release-approved')
  if (blocked.status !== 'ready') throw new Error(`unexpected release status: ${blocked.status}`)
  const state = JSON.parse(await readFile(blocked.statePath, 'utf8'))
  if (state.mode !== 'dry-run' || state.events.length === 0) throw new Error('runner state lacks mode or stage events')
  const host = invokeHost('--task', 'host execution', '--scope', 'fixtures', '--acceptance', 'host handoff works')
  if (host.status !== 'awaiting-host-execution' || host.mode !== 'host-managed') throw new Error('host-managed handoff failed')
  const hostState = JSON.parse(await readFile(host.statePath, 'utf8'))
  if (hostState.mode !== 'host-managed' || hostState.events[0]?.type !== 'host-handoff') throw new Error('host state lacks handoff event')
  console.log('OK: workflow runner dry-run, host-managed handoff, approvals, bounded reviews, and state persistence')
} finally {
  await rm(new URL(`.claude/workflow-state/${runId}.json`, new URL('..', import.meta.url)), { force: true })
  await rm(new URL(`.claude/workflow-state/${hostRunId}.json`, new URL('..', import.meta.url)), { force: true })
}
