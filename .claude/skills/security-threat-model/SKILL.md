---
name: security-threat-model
model: opus
description: Works out how a feature could be attacked before it is built - who the attacker is, what they want, where the trust boundaries are and what fails first. Use for "is this design secure", "threat model this", "how could this be abused", "what could go wrong security-wise", "we are handling payments now", "this endpoint is public", "users can upload files", "what are the attack vectors". Prefer this over scanning the code after it is written - the expensive vulnerabilities are design decisions, and a scanner cannot see a missing trust boundary. Do NOT use for scanning existing code; those are the security-authz-check, security-injection-scanner and security-dependency-audit skills.
---

# Security Threat Model

Design-time. The `security-*` scanners find implementation flaws; this finds the design
decisions that make whole classes of flaw possible.

## Steps

1. **Draw the trust boundaries.** Every point where data crosses from less-trusted to
   more-trusted is where controls belong. Most designs have more boundaries than the author
   thinks - a background job reading a user-supplied field is one.
2. **Name the attackers concretely** - anonymous internet, authenticated user attacking
   another user, insider, compromised dependency. Different attackers reach different
   surfaces, and "a hacker" is not a threat model.
3. **For each boundary, ask what the attacker controls** - fully, partially, or not at all.
   Partially-controlled input is where the interesting bugs live.
4. **Walk the classic categories** rather than relying on inspiration: spoofing, tampering,
   repudiation, information disclosure, denial of service, elevation of privilege.
5. **Rank by reachability, not severity.** A critical bug behind three authentication walls
   matters less than a moderate one on an unauthenticated endpoint.
6. **Assign each threat a control**, and note which are absent by decision versus by
   oversight. The recorded decision is what stops it being relitigated forever.

## Rules

- **Assume the client is hostile.** Any check that exists only in the UI does not exist.
- **Handle the abuse case, not just the error case.** Malformed input is an error; crafted
  input is an attack, and they need different handling.
- Record accepted risks explicitly - an unrecorded accepted risk is indistinguishable from
  one nobody noticed.


## Routing

**Validator (required): `.claude/validators/security-secrets-scan.md`.** CLAUDE.md makes this mandatory
before any side effect is committed - it is not optional cleanup after the fact. Run it and
report the result; a skipped validator is a failed run, not a fast one.
