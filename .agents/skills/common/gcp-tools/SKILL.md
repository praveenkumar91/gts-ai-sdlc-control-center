---
name: gcp-tools
description: "Inquire/create/start/stop GCP instances for T7 development via gts.gcp.tools scripts. Use when: to create GCP development or test machines, esp. to run complete GTS runtime environments, e.g. for smoketest. Generally to control GCP instances. Only runs on GCP machines."
---

# Overview

This skill provides facilities to inquire/create/start/stop GCP instances which can be used as development or test machines for T7 (e.g. to host complete GTS environments). It uses the scripts provided in `gts.gcp.tools/t7-scripts/` to interact with GCP.

It only runs on GCP machines. If you're running on a local/on-prem machine, SSH to a GCP machine and execute the skill over there. You might use any running GCP machine you know, or ask the user for an existing, running machine, or ask the user to start/create one manually via [Cloud Admin Cockpit](https://t7clouddev.deutsche-boerse.de/).

# Configuration Reference

| Parameter | Default | Notes |
|---|---|---|
| GCP project | `dbg-t7-shared-sz-dev-cd` | account name alias: `sz` |
| Default zone | `europe-west3-a` (Frankfurt) | |
| Default image family | `t7-redhat88-devel` | |
| Default disk size | 50 GB | |
| Default instance size | `n1-standard-4` | |

**Available GCP projects / account names:**

| GCP Project ID | Account name (`--account`) |
|---|---|
| `dbg-derivatives-dev-13743755` | `dev-sandbox` |
| `dbg-t7-shared-sz-dev-cd` | `sz` |
| `dbg-t7-shared-dev-e7` | `dev` |

**Available zones:**
- `europe-west3-a/b/c` – Frankfurt
- `europe-west4-a/b/c` – Amsterdam/Netherlands
- `europe-north1-a/b/c` – Finland
- `europe-west1-b/c/d` – Belgium

**Available image families:** `rhel-88-byos-gts`, `t7-redhat88-base`, `t7-redhat88-test`, `t7-redhat88-devel`, `t7-redhat88-build`

---

# Inquire: List Instances

Script: `listT7Instances.py`

```
listT7Instances.py [-i INSTANCEID [INSTANCEID ...]] [-n NAME] [-o OWNER]
                   [-s STATUS [...]] [-v]
```

| Option | Description |
|---|---|
| `-i`/`--instanceid` | Filter by instance ID(s) |
| `-n`/`--name` | Filter by name (wildcards allowed, e.g. `*EUREX*`) |
| `-o`/`--owner` | Filter by owner (wildcards allowed) |
| `-s`/`--status` | Filter by status: `PROVISIONING`, `STAGING`, `RUNNING`, `STOPPING`, `STOPPED`, `SUSPENDING`, `SUSPENDED`, `TERMINATED` |
| `-v`/`--verbose` | Debug output |

Example – list all running instances:
```
listT7Instances.py -s RUNNING
```

Example – list all instances by owner:
```
listT7Instances.py -o myusername
```

---

# Create: Run a New Instance

Script: `runT7Instance.py`

```
runT7Instance.py -n NAME -j PROJECT [options]
```

**Required:**

| Option | Description |
|---|---|
| `-n`/`--name` | Instance name (unique key, must not already exist) |
| `-j`/`--project` | Billing/purpose tag – must be a known project value (see list below) |

**Common optional parameters:**

| Option | Default | Description |
|---|---|---|
| `-k`/`--keyfile` | `~/.ssh/id_rsa.pub` | SSH public key to inject |
| `-s`/`--size` | `n1-standard-4` | Instance type, e.g. `n1-standard-8`, `n1-highmem-8` |
| `-d`/`--disksize` | `50` | Root partition size in GB (minimum 50) |
| `-z`/`--zone` | `europe-west3-a` | GCP zone |
| `-r`/`--region` | — | GCP region (alternative to zone) |
| `-f`/`--imagefamily` | `t7-redhat88-devel` | Image family to use |
| `-i`/`--imagename` | — | Use a specific image instead of the latest in a family |
| `--account` | `sz` | Account/project context (`dev-sandbox`, `sz`, `dev`) |
| `--spot` | off | Request a spot (preemptible) instance |
| `-o`/`--owner` | current user | Owner label for billing |
| `-x`/`--autoshutdowntime` | 19:00 (on-demand) | Auto-shutdown time `HH_MM`; set to `off` to disable |
| `--autoterminationtime` | off | Auto-termination time `HH_MM` |
| `--terminationprotection` | off | Enable deletion protection (must disable in GCP console before terminating) |
| `--nowait` | off | Do not wait for instance to become ready |
| `--dnsname` | — | Register a DNS record for the instance IP |

**`--project` values (billing tag, NOT GCP project):**
`ci-smoketest`, `ci-build`, `cre-development`, `t7-eurex-regression`, `t7-functional-test`, `t7-prague-dev-core`, `t7graphql-development`, `t7-sdk`, `t7-opm-development`, `t7-xeidea`, `t7-rds`, `t7-networks-trading` … (full list in `t7-scripts/gtsutils/config.py`)

Example – create a development instance:
```
runT7Instance.py -n myname-dev-01 -j cre-development -s n1-standard-8 -f t7-redhat88-devel
```

After creating, verify:
```
listT7Instances.py -n myname-dev-01
```

---

# Start: Start a Stopped Instance

Script: `startT7Instance.py`

```
startT7Instance.py [--nowait] [-z ZONE] [-v] MACHINE [MACHINE ...]
```

| Option | Description |
|---|---|
| `MACHINE` | One or more instance names or IP addresses |
| `-z`/`--zone` | Zone to search in (default: searches all zones) |
| `--nowait` | Do not wait for the start to complete |
| `-v`/`--verbose` | Debug output |

Example:
```
startT7Instance.py myname-dev-01
```

After starting, verify:
```
listT7Instances.py -n myname-dev-01 -s RUNNING
```

---

# Stop: Stop a Running Instance

Script: `stopT7Instance.py`

```
stopT7Instance.py [--this] [--nowait] [-z ZONE] [-v] [MACHINE ...]
```

| Option | Description |
|---|---|
| `MACHINE` | One or more instance names or IP addresses |
| `--this` | Stop the instance on which the script is being executed |
| `-z`/`--zone` | Zone to search in (default: searches all zones) |
| `--nowait` | Do not wait for completion |
| `-v`/`--verbose` | Debug output |

Example:
```
stopT7Instance.py myname-dev-01
```

After stopping, verify:
```
listT7Instances.py -n myname-dev-01 -s STOPPED
```

---

# Terminate: Permanently Delete an Instance

> **Irreversible.** Verify the target carefully before proceeding. Ask the user to confirm.

Script: `terminateT7Instance.py`

```
terminateT7Instance.py [--this] [--nowait] [-z ZONE] [-v] [MACHINE ...]
```

Options are the same as `stopT7Instance.py`. Termination permanently deletes the instance and its local disk.

If the instance has deletion protection enabled, the user must first disable it in the GCP console or via `changeT7InstanceDeletionProtection.py --off`.

---

# Additional Scripts

## Get Instance Metadata (from inside a GCP instance)

```
getT7InstanceMetadata.py [-i ITEM]
```

`-i`/`--item` fetches a specific metadata item, e.g. `service-accounts/default/email`. Without `-i`, displays all metadata.

## List Available Images

```
listT7Images.py
```

No parameters. Lists all T7 and base images across projects.

## Resize an Instance

```
resizeT7Instance.py -i INSTANCE [-s SIZE] [-c CPU] [-r RAM] [-z ZONE] [-p PROJECT] [-v]
```

Stops the instance, applies the new size, and starts it again.

## Increase Disk Volume (run on the instance itself)

```
increaseT7Volume.py -s SIZE [-v]
```

`-s SIZE` is the new total size in GB, or use `+N` to add N GB (e.g. `+200`).

## Manage Labels

```
labelT7Instance.py [-l] [-s LABEL=VALUE] [-d LABEL] [--this] [-z ZONE] [-v] [MACHINE ...]
```

| Option | Description |
|---|---|
| `-l`/`--list` | List labels on instance(s) |
| `-s`/`--set` | Set a label as `key=value` |
| `-d`/`--delete` | Delete a label by name |
| `--this` | Target the current instance |

## Change Deletion Protection

```
changeT7InstanceDeletionProtection.py (--on|--off) [--this] [-z ZONE] [-v] [MACHINE ...]
```

---

# Fallback: CloudDev Cockpit

If scripts are not available or produce authentication errors, direct the user to the web cockpit:

`https://t7clouddev.deutsche-boerse.de/`

---

# Safety Rules

- Never run `terminateT7Instance.py` without explicit user confirmation and a clearly identified target.
- For ambiguous instance names, run `listT7Instances.py` first to disambiguate.
- After every create/start/stop/terminate action, re-run `listT7Instances.py` to confirm the expected final state.
- If deletion protection is set and termination is needed, remind the user it must be disabled first.

# References

All scripts live in `gts.gcp.tools/t7-scripts/`.