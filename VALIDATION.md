# MA2500D API compatibility validation

Contribution base: `d477493fe9c82afd2ca28ef0f5264c6d1c251e9c`.
Validation date: November 17, 2026.

## Scope

Correct the MA2500D firmware 2.0.16.0 HTTP getter protocol and status decoding:
POST payloads, cookie/CSRF sessions, node 0, controller/active-node fields,
unsigned packet counters, packed directional PHY data, and the existing
band/frequency/channel-count/encryption entities. Existing entity unique IDs
are retained. Peer entities follow MAC identity through discovery/reordering
and become unavailable when the peer or its reading disappears.

The contribution retains the upstream name, repository references, ownership,
version and planned features. It adds no Ethernet-link/SDK/channel-detail sensors,
deployment tooling, configuration controls, write requests or key retrieval.

## Hardware baseline

The underlying implementation was exercised against two physical MA2500D adapters
and subsequently reported working in HA by the operator. Firmware image version
2.0.16.0 was reported by the operator, not inferred from the SoC SDK string.

The focused contribution passed setup and two polls against both adapters with
27 allowlisted requests per device and PHY rates around 3.4 Gbps. Checks cover
stable local MAC identity, reciprocal peer association, controller/node IDs,
link up, one peer, five channels, directional
PHY rates, non-decreasing counters, configured-band/privacy flags and a traced
target/method/path allowlist. Private captures and credentials are not published.

## Automated regression baseline

- **34 portable protocol/HTTP tests passed**: Python 3.12 and aiohttp 3.14.5. Tests cover captured
  layouts, sparse masks, unsigned 64-bit counters, missing optional data, strict
  request validation, cookie/CSRF initialization and refresh, bounded retries,
  authentication failures, refused redirects and bounded/malformed responses.
- **23 HA tests passed**: Linux Python 3.14, Home Assistant 2026.10.4 and
  pytest-homeassistant-custom-component 0.13.375. Tests cover config flows,
  setup/unload/session cleanup, coordinator failures, diagnostics redaction,
  entity IDs and peer discovery/reordering/departure. Device HTTP is mocked.
- Ruff lint/format and Git whitespace checks.
- GitHub Actions runs separate portable-client and HA regression jobs.

## Limits and additional testing requested

Hardware validation covers only two MA2500D devices on firmware 2.0.16.0. The
previously listed MA2500D 2.0.11, MA2500C 3.0.5, WF-803M and Frontier variants
have not been retested with this client. Maintainer/community testing on those
combinations is requested before treating the change as broadly compatible.
Mixed-version and sixteen-node networks are not hardware-validated; sparse masks
have synthetic regression coverage.

Firmware image/model/SNR/power metadata remains unknown without a verified source.
Configured encryption flags are not an independent cryptographic audit. HTTP
management traffic remains unencrypted. No production HA instance was contacted,
changed, reloaded or restarted while preparing this contribution.
