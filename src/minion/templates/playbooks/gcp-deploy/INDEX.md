# Playbook family: gcp-deploy

> Deploy a containerized web app to a single small GCP VM, from a devbox
> acting as control plane. Generic templates — replace `{{PLACEHOLDERS}}`
> per project, or resolve them from the operator's global CLAUDE.md.
>
> Reusable across projects. First proven instance: **toto-mondiale**
> (`~/projects/toto-mondiale/infra/`), which is the concrete IaC these
> runbooks describe. Copy that `infra/` shape into the next project and
> re-fill the parameters.

## Shape of the target

```
devbox (control plane)
  ├─ terraform/  -> GCP: VPC (no ingress), VM, service account, budget
  └─ ansible/    -> over Tailscale SSH: hardening, docker, app deploy

small GCP VM (e.g. e2-micro Always Free, US region)
  - zero open inbound ports
  - app   reached via Cloudflare Tunnel (cloudflared dials out)
  - admin reached via Tailscale SSH (egress-initiated)
  - image built on the devbox, pushed to a registry, pulled by the VM
  - Watchtower polls the registry and auto-updates the running app
```

## Why this architecture

- **No public ports.** Both ingress (Tunnel) and admin (Tailscale) are
  egress-initiated overlays. The VPC has no ingress allow rules.
- **Build off-box.** A 1 GB VM OOMs on most production builds. Build on
  the devbox, push to the registry, pull a ready image on the VM.
- **Stateless app.** JWT sessions / no DB on the box means no volume, no
  backup, no migration on the VM — the VM is cattle, rebuildable from code.
- **Remote TF state.** State in a GCS bucket survives loss of the devbox
  and lets the VM be torn down / rebuilt deterministically.

## Run order (each step has a playbook)

| # | Playbook | Concern | Where it runs |
|---|---|---|---|
| 1 | `gcp-project-bootstrap.md` | project, billing, ADC, APIs, GCS state bucket | devbox + console |
| 2 | `terraform-gce-vm.md` | provision VPC + VM + SA + budget | devbox (terraform) |
| 3 | `tailscale-join-vm.md` | VM joins the tailnet (channel for Ansible) | startup script / verify |
| 4 | `ghcr-publish.md` | build on devbox, push image to the registry | devbox (docker) |
| 5 | `cloudflare-tunnel.md` | create the tunnel, get the token | console |
| 6 | `vm-provision-ansible.md` | hardening + docker + app deploy + watchtower | devbox (ansible) |
| 7 | `oauth-prod-wiring.md` | add prod redirect URI / origin to the OAuth client | console |

Steps 1–2 stand up the box; 4–5 produce the image and the ingress token;
6 ties them together on the VM; 3 and 7 are verify/wire steps.

## What this family does NOT do

- Does **not** create the GCP account or the registry account.
- Does **not** register the domain or change nameservers (that is the
  Cloudflare onboarding step the operator does in the dashboard).
- Does **not** manage a database, backups, or stateful volumes — the app
  is assumed stateless. A stateful variant is a separate family.
