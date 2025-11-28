# E University - EVE-NG Topology Cabling Guide

## Network Diagram

```
                                 INTERNET
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
              EUNIV-INET-GW1                 EUNIV-INET-GW2
              (.206)                         (.207)
                    │ Gi2                           │ Gi2
                    │                               │
                    │ Gi4                           │ Gi4
              ┌─────┴─────┐                   ┌─────┴─────┐
              │           │                   │           │
              ▼           │                   │           ▼
        EUNIV-CORE1 ══════╪═══════════════════╪════ EUNIV-CORE2
        (.200) RR    Gi2  │         Gi2       │ Gi2  (.202) RR
              │           │                   │           │
         Gi3  │           │                   │           │ Gi3
              │           │                   │           │
        EUNIV-CORE5 ══════╪═══════════════════╪════ EUNIV-CORE3
        (.205) RR    Gi2  │         Gi2       │ Gi2  (.203)
              │           │                   │           │
         Gi3  │           │                   │           │ Gi3
              │           └───────┬───────────┘           │
              │                   │                       │
              │             EUNIV-CORE4                   │
              │             (.204)                        │
              │              Gi2 │ Gi3                    │
              └──────────────────┴────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         │ Gi5              Gi4  │  Gi5                  │ Gi4
         ▼                       ▼                       ▼
   EUNIV-MAIN-AGG1        EUNIV-MED-AGG1         EUNIV-RES-AGG1
   (.208)                 (.211)                  (.214)
    Gi4 │ Gi5              Gi4 │ Gi5               Gi4 │ Gi5
        │                      │                       │
   ┌────┴────┐            ┌────┴────┐             ┌────┴────┐
   │         │            │         │             │         │
   ▼         ▼            ▼         ▼             ▼         ▼
MAIN-PE1  MAIN-PE2     MED-PE1  MED-PE2       RES-PE1  RES-PE2
(.209)    (.210)       (.212)   (.213)        (.215)   (.216)
   │         │            │         │             │         │
   └────┬────┘            └────┬────┘             └────┬────┘
      Gi3                    Gi3                     Gi3
   (HA Link)              (HA Link)               (HA Link)
```

## Interface Assignments

### Management Network (Connect to your home network)
All devices: **GigabitEthernet1** → EVE-NG Cloud/Bridge to home network

---

## Core Ring Connections

| Cable | Device A | Interface A | Device B | Interface B | Subnet |
|-------|----------|-------------|----------|-------------|--------|
| 1 | EUNIV-CORE1 | Gi2 | EUNIV-CORE2 | Gi2 | 10.0.0.0/30 |
| 2 | EUNIV-CORE2 | Gi3 | EUNIV-CORE3 | Gi2 | 10.0.0.4/30 |
| 3 | EUNIV-CORE3 | Gi3 | EUNIV-CORE4 | Gi2 | 10.0.0.8/30 |
| 4 | EUNIV-CORE4 | Gi3 | EUNIV-CORE5 | Gi2 | 10.0.0.12/30 |
| 5 | EUNIV-CORE5 | Gi3 | EUNIV-CORE1 | Gi3 | 10.0.0.16/30 |

## Internet Gateway Connections

| Cable | Device A | Interface A | Device B | Interface B | Subnet |
|-------|----------|-------------|----------|-------------|--------|
| 6 | EUNIV-CORE1 | Gi4 | EUNIV-INET-GW1 | Gi2 | 10.0.0.20/30 |
| 7 | EUNIV-CORE2 | Gi4 | EUNIV-INET-GW2 | Gi2 | 10.0.0.24/30 |

## Main Campus Connections

| Cable | Device A | Interface A | Device B | Interface B | Subnet |
|-------|----------|-------------|----------|-------------|--------|
| 8 | EUNIV-CORE1 | Gi5 | EUNIV-MAIN-AGG1 | Gi2 | 10.0.1.0/30 |
| 9 | EUNIV-CORE2 | Gi5 | EUNIV-MAIN-AGG1 | Gi3 | 10.0.1.4/30 |
| 10 | EUNIV-MAIN-AGG1 | Gi4 | EUNIV-MAIN-PE1 | Gi2 | 10.0.1.8/30 |
| 11 | EUNIV-MAIN-AGG1 | Gi5 | EUNIV-MAIN-PE2 | Gi2 | 10.0.1.12/30 |
| 12 | EUNIV-MAIN-PE1 | Gi3 | EUNIV-MAIN-PE2 | Gi3 | 10.0.1.16/30 |

## Medical Campus Connections

| Cable | Device A | Interface A | Device B | Interface B | Subnet |
|-------|----------|-------------|----------|-------------|--------|
| 13 | EUNIV-CORE2 | Gi6 | EUNIV-MED-AGG1 | Gi2 | 10.0.2.0/30 |
| 14 | EUNIV-CORE3 | Gi4 | EUNIV-MED-AGG1 | Gi3 | 10.0.2.4/30 |
| 15 | EUNIV-MED-AGG1 | Gi4 | EUNIV-MED-PE1 | Gi2 | 10.0.2.8/30 |
| 16 | EUNIV-MED-AGG1 | Gi5 | EUNIV-MED-PE2 | Gi2 | 10.0.2.12/30 |
| 17 | EUNIV-MED-PE1 | Gi3 | EUNIV-MED-PE2 | Gi3 | 10.0.2.16/30 |

## Research Campus Connections

| Cable | Device A | Interface A | Device B | Interface B | Subnet |
|-------|----------|-------------|----------|-------------|--------|
| 18 | EUNIV-CORE4 | Gi4 | EUNIV-RES-AGG1 | Gi2 | 10.0.3.0/30 |
| 19 | EUNIV-CORE5 | Gi4 | EUNIV-RES-AGG1 | Gi3 | 10.0.3.4/30 |
| 20 | EUNIV-RES-AGG1 | Gi4 | EUNIV-RES-PE1 | Gi2 | 10.0.3.8/30 |
| 21 | EUNIV-RES-AGG1 | Gi5 | EUNIV-RES-PE2 | Gi2 | 10.0.3.12/30 |
| 22 | EUNIV-RES-PE1 | Gi3 | EUNIV-RES-PE2 | Gi3 | 10.0.3.16/30 |

---

## EVE-NG Setup Steps

### 1. Create New Lab
- Name: `E-University-Network`
- Description: `Multi-campus BGP/MPLS network`

### 2. Add 16 Nodes
Use **Cisco IOSv** or **CSR1000v** image for all devices.

### 3. Add Cloud Network
- Add a "Cloud" or "Network" object
- Connect to your home network bridge (e.g., `pnet0`)
- This gives all devices management connectivity

### 4. Connect Management (Gi1)
Connect each device's **Gi1** to the Cloud network

### 5. Connect Core Ring
Follow the cabling table above for Gi2, Gi3, etc.

### 6. Apply Startup Configs
For each device:
1. Right-click → Edit
2. Paste the startup config from `startup-configs/DEVICE.cfg`
3. Or use the startup-config import feature

### 7. Start All Nodes

### 8. Verify Management Connectivity
```bash
ping 192.168.68.200  # CORE1
ping 192.168.68.216  # RES-PE2
```

---

## Total Connections Summary

| Category | Count |
|----------|-------|
| Management (to Cloud) | 16 |
| Core Ring | 5 |
| Internet Gateways | 2 |
| Main Campus | 5 |
| Medical Campus | 5 |
| Research Campus | 5 |
| **Total Cables** | **38** |

---

## Image Requirements

- **Recommended**: Cisco CSR1000v or Cisco IOSv
- **RAM per device**: 3-4 GB for CSR1000v, 512MB-1GB for IOSv
- **Total RAM needed**: ~16-24 GB for full lab with CSR1000v

## Quick Tip for EVE-NG

To import startup configs automatically:
1. Place configs in `/opt/unetlab/addons/qemu/csr1000v-xxx/` 
2. Or use EVE-NG's startup-config feature when creating nodes
