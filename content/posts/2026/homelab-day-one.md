---
title: "Saturday homelab: an AI pair-programming experiment"
date: 2026-03-28T18:00:00+01:00
draft: false
tags: ['homelab', 'proxmox', 'jellyfin', 'ai', 'claude']
---

I spent a Saturday turning a dusty 2011 MacBook Pro into a home server. By evening I had Jellyfin streaming Twin Peaks to the TV, a download client with built-in search, and a bedside lamp I could control from my phone. It took about 8 hours. Most of that was fighting my ISP router.

Here's the thing though - I didn't write a single line of config. Claude did all of it. I just told it what I wanted and pasted error messages when things broke.

## How this actually worked

I had the idea and the hardware. A MacBook Pro gathering dust, a vague notion that Proxmox exists, and zero experience with Linux server administration. I knew what I wanted the end result to look like - media streaming, smart home control, remote access - but I didn't know how to get there.

So I opened Claude Code, described what I had and what I wanted, and let it drive. It wrote the shell commands, I ran them. When something failed, I pasted the output back. When I was curious about why we were doing something a certain way - why LXC containers instead of full VMs for Jellyfin, what Tailscale subnet routing actually does, why inotify doesn't work across bind mounts - I'd ask, and Claude would explain it.

The dynamic was closer to directing a contractor than to following a tutorial. I made the decisions (what to install, where to put things, how to organize the media library), Claude handled the implementation details (the actual `pct set` flags, systemd service files, mount point permissions).

## The ISP router rabbit hole

This is where the human-in-the-loop part actually mattered. Half the day went to discovering that my ZTE F680 (ISP-provided fiber router) isolates everything from everything. Not just WiFi from ethernet - it isolates its own LAN ports from each other. Port 1 can't talk to port 2.

No amount of AI assistance helps when the problem is physical. I was the one moving the laptop between floors, swapping ethernet cables, checking which devices could see which. Claude helped me run the diagnostic commands (`ip neigh show`, ARP resolution tests) and interpret the results, but the actual debugging was me walking around the apartment with a laptop under my arm.

We eventually confirmed that the isolation is baked into the ZTE firmware. The SSID Isolation toggle in settings was already off. Doesn't matter. Locked-down ISP build, no advanced bridging options exposed.

My current workaround is duct tape: a D-Link on the second floor as a switch and WiFi AP, a Netgear range extender bridging WiFi between floors, and the lamp moved from ZTE's WiFi to D-Link's WiFi just so Home Assistant could see it.

The fix is simple - buy a proper router (TP-Link Archer AX55, ~50 EUR), put the ISP box in bridge mode, one flat network. Should've done that before starting.

## What Claude actually set up

Once we got past the networking issues, the rest went fast. I'd describe what I wanted, Claude would give me the commands, I'd run them.

**Proxmox** - flashed the ISO myself (Claude can't do that), but Claude handled post-install config. Disabling lid-close suspend, setting up Tailscale with subnet routing, creating VMs and containers with the right resource allocations.

**Home Assistant** - Claude walked me through creating the HAOS VM and configuring the passthrough settings. Once it was running, HA's auto-discovery found my Xiaomi lamp immediately (after I moved it to the right network). Using the HomeKit Controller integration - fully local, no cloud, no Xiaomi account. I asked Claude why HomeKit instead of the Xiaomi integration, and the answer (local-only, no cloud dependency, works even if Xiaomi shuts down their servers) made sense.

**Jellyfin + qBittorrent** - this is where Claude did the most work. Setting up the LXC container, mounting the storage drive, installing and configuring both services, creating systemd units, setting up media directory structure. I just decided the folder layout (`movies`, `tv`, `concerts`) and which search plugins to install.

**Static IPs and DNS** - Claude caught that containers would lose their IPs on reboot before I even noticed. Also fixed a Tailscale DNS issue where containers inherited the host's DNS config and couldn't resolve anything.

## Things I picked up along the way

I didn't set out to learn Linux administration, but you absorb things when you're watching every command run and asking "why?" when something isn't obvious.

**LXC vs full VMs.** Containers share the host kernel and use way less RAM. Jellyfin doesn't need its own kernel, so an LXC container is the right call. Home Assistant needs its own OS (HAOS), so that's a full VM.

**Bind mounts and inotify.** Jellyfin's real-time library scanner doesn't detect new files on bind-mounted volumes. Something about how filesystem event notifications work across mount boundaries. Scheduled scan every 30 minutes instead.

**Codec transcoding economics.** Old .avi files (DivX/MPEG4) need software transcoding, which hammers the CPU on this old hardware. Modern x264 .mkv files play directly on the TV without any server-side work. I asked Claude about hardware transcoding (Intel QuickSync), and it explained that the 2011 HD 3000 only supports H264 decode - which is the one codec that doesn't need transcoding anyway.

**Container resource sizing.** Started with 2GB RAM for the Jellyfin container. With qBittorrent downloading in the background, it hit 97% CPU and 99% swap. Claude bumped it to 4GB and 4 cores after I pasted the `htop` output.

## The meta-experiment

This was partly about the homelab and partly about testing how far you can get with an AI doing the implementation while you handle the physical world and the decision-making.

The answer: pretty far. I went from "I've never administered a Linux server" to a working setup in a day. But the interesting part is what didn't work without me. The physical debugging (network isolation), the taste decisions (what media to organize how), the error recovery when Claude's commands didn't account for my specific hardware - that all required a human in the loop.

Claude was also wrong sometimes. It initially suggested a resource allocation that was too small. It didn't anticipate the Tailscale DNS conflict until I hit it. It couldn't know that my ISP router was broken in a way that isn't documented anywhere. The AI was a great implementer but a mediocre planner, because planning requires knowing the actual state of the world.

## Hardware

For reference:

- MacBook Pro 2011, i7, 16GB RAM, 100GB SSD + 500GB HDD
- HA VM: 8GB RAM, 32GB disk
- Jellyfin LXC: 4GB RAM, 4 cores, 16GB disk + 500GB HDD mount
- Can handle 1-2 simultaneous streams with software transcoding
- Library of ~100GB so far with room for ~400GB more

Total cost: 0 EUR (had the laptop lying around). Should've spent 50 EUR on a router.

## What's next

- **Replace the ISP router.** TP-Link Archer AX55 (~50 EUR), ZTE demoted to bridge mode. One flat network, no isolation.
- **Zigbee sensor network.** USB Zigbee coordinator dongle passed through to the HA VM, temperature sensors in each room, IKEA smart plugs as mesh routers. ~100 EUR total, everything local through HA.
- Sonos integration with Home Assistant - TTS announcements, morning briefings
- Pi-hole for network-wide ad blocking
- More storage when the HDD fills up
