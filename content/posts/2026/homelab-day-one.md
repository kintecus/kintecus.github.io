---
title: "Homelab in an hour (not the 8 it took me)"
date: 2026-03-28T18:00:00+01:00
draft: false
tags: ['homelab', 'proxmox', 'jellyfin', 'networking']
---

I spent a Saturday turning a dusty 2011 MacBook Pro into a home media server with Home Assistant. By evening I had Jellyfin streaming Twin Peaks to the TV, a download client with built-in search, and a bedside lamp I could control from my phone. It took about 8 hours. Most of that was fighting my ISP router.

Here's how to do it in one.

## Skip the ISP router

Single biggest time-saver. I lost half the day discovering that my ZTE F680 (ISP-provided fiber router) isolates everything from everything. Not just WiFi from ethernet - it isolates its own LAN ports from each other. Port 1 can't talk to port 2. The SSID Isolation toggle in settings was already off. Doesn't matter. Baked into the firmware, locked-down ISP build, no advanced bridging options exposed.

I confirmed this the hard way - moved the Proxmox server between floors, tried every LAN port combination, ran ARP resolution tests. All failed. `ip neigh show` just returns `FAILED` for anything not on the same physical switch. TV on LAN port 3 can't reach the server on LAN port 2. Lamp on WiFi can't see anything on ethernet. Nothing works through the ZTE.

My current setup is duct tape: a D-Link on the second floor as a switch and WiFi AP, a Netgear range extender bridging WiFi between floors, Tailscale port forwards for devices that can't reach the server, and the lamp moved from ZTE's WiFi to D-Link's WiFi just so Home Assistant could see it.

**What to do instead:** buy a proper router before starting. TP-Link Archer AX55, about 50 EUR. Put the ISP box in bridge mode (it just handles the fiber connection), let the real router handle everything else. One flat network, one SSID, every device talks to every other device.

Two floors? Add a second AP connected via ethernet. Same SSID, different channel. Devices roam seamlessly.

Do this first. Everything else becomes trivial.

## The actual one-hour setup

Assuming you have a proper network and an old laptop with 8+ GB RAM:

### Proxmox (15 min)

Flash the Proxmox ISO to a USB stick, boot from it, click through the installer. Debian-based hypervisor with a web UI. Not much to configure.

If you're using a laptop, disable lid-close suspend before closing the lid:

```bash
sed -i 's/#HandleLidSwitch=suspend/HandleLidSwitch=ignore/' /etc/systemd/logind.conf
sed -i 's/#HandleLidSwitchExternalPower=suspend/HandleLidSwitchExternalPower=ignore/' /etc/systemd/logind.conf
systemctl restart systemd-logind
```

Install Tailscale on PVE for remote access. Enable subnet routing so you can reach all your VMs/containers from anywhere:

```bash
tailscale set --advertise-routes=192.168.1.0/24
```

Approve the route in the Tailscale admin console.

### Home Assistant (10 min)

Download the HAOS (Home Assistant OS) VM image. Create a VM in Proxmox, attach the image, boot it. Setup wizard walks you through everything. Give it 4GB RAM.

If your network is flat (see above), HA auto-discovers most devices. My Xiaomi lamp showed up immediately once it was on the same network segment. Using the HomeKit Controller integration - fully local, no cloud, no Xiaomi account needed.

### Jellyfin + media downloads (20 min)

Create an Ubuntu LXC container. Give it 4GB RAM, 4 cores. Mount your storage drive:

```bash
mkdir -p /mnt/ssd/media/{movies,tv,concerts,downloads}
chmod 777 /mnt/ssd/media/*
pct set 100 -mp0 /mnt/ssd/media,mp=/media
```

Install Jellyfin:

```bash
# Add Jellyfin repo and install (follow jellyfin.org/docs/general/installation/linux)
apt install jellyfin
```

Install qBittorrent:

```bash
apt install qbittorrent-nox
```

Run qBittorrent as a systemd service so it starts on boot. It has a built-in search plugin system - install a few and you can find and grab media directly from the web UI.

Set the default save path to your media directory, create categories for `tv`, `movies`, `concerts` pointing to the right subdirectories. Bypass auth for the local subnet so you don't have to log in from home.

**Important:** Jellyfin needs media organized as `Show Name/Season XX/episode.mkv` for TV shows. Loose files in a folder won't be detected as shows.

### Static IPs and DNS (5 min)

Set static IPs for your containers in Proxmox. DHCP will change the IP on every reboot and break all your bookmarks.

```bash
pct set 100 -net0 name=eth0,bridge=vmbr0,ip=192.168.1.99/24,gw=192.168.1.1
```

If your containers can't resolve DNS (common if PVE uses Tailscale DNS):

```bash
pct set 100 -nameserver "1.1.1.1 8.8.8.8"
```

### Streaming (10 min)

Install the Jellyfin app on your TV (Android TV has it in the Play Store), phone, tablet. Point them at `http://<jellyfin-ip>:8096`. Done.

On iOS, Swiftfin is more reliable than the official Jellyfin app.

## Things I learned the hard way

**Container resources matter.** Started the Jellyfin LXC with 2GB RAM. With qBittorrent downloading in the background, it hit 97% CPU and 99% swap. Web UI became unusable. 4GB RAM and 4 cores is the minimum for a combined setup.

**inotify doesn't cross bind mounts.** Jellyfin's real-time library monitoring won't detect new files on a bind-mounted volume. Use a scheduled library scan instead - every 30 minutes works fine.

**Codec compatibility.** Old .avi files (DivX/MPEG4) need software transcoding, which hammers the CPU. Modern x264 .mkv files direct-play on almost every TV without transcoding. When grabbing content, look for `x264` or `H.264`.

**Tailscale DNS breaks containers.** LXC containers inherit the host's `/etc/resolv.conf`, which points to Tailscale's DNS (`100.100.100.100`). Containers don't have Tailscale, so DNS fails and `apt-get update` hangs. Fix: `pct set <vmid> -nameserver "1.1.1.1 8.8.8.8"`.

**Intel QuickSync on old hardware is useless.** The 2011 MacBook's HD 3000 only supports H264 decoding via QSV. Most files that need transcoding are old codecs (not H264), so hardware acceleration doesn't help. Enabled it, reverted to software transcoding.

## My hardware

For reference:

- MacBook Pro 2011, i7, 16GB RAM, 100GB SSD + 500GB HDD
- HA VM: 8GB RAM, 32GB disk
- Jellyfin LXC: 4GB RAM, 4 cores, 16GB disk + 500GB HDD mount
- Can handle 1-2 simultaneous streams with software transcoding
- Library of ~100GB so far with room for ~400GB more

Total cost: 0 EUR (had the laptop lying around). Should've spent 50 EUR on a router.

## What's next

- **Replace the ISP router.** A TP-Link Archer AX55 (~50 EUR) as the actual router, ZTE demoted to bridge mode. One flat network, no isolation. This is the single change that would've saved me most of the 8 hours.
- **Zigbee sensor network.** A USB Zigbee coordinator dongle (Sonoff ZBDongle-E, ~60 PLN) passed through to the HA VM, with Aqara temperature/humidity sensors in each room and IKEA INSPELNING smart plugs as mesh routers. Total cost for the whole setup: around 400 PLN (~100 EUR). No proprietary hubs needed - everything runs locally through HA's ZHA integration.
- Add Sonos integration to Home Assistant
- Pi-hole for network-wide ad blocking
- More storage via USB external drives when the HDD fills up
