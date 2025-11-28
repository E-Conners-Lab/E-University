
# E-University Network Design Document

**Document Version:** 1.0  
**Date:** November 27, 2025  
**Author:** Network Engineering Team  
**Classification:** Internal Use

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Network Architecture Overview](#2-network-architecture-overview)
3. [Device Inventory](#3-device-inventory)
4. [Physical Topology](#4-physical-topology)
5. [IP Addressing Plan](#5-ip-addressing-plan)
6. [Routing Design](#6-routing-design)
7. [MPLS Design](#7-mpls-design)
8. [VRF Design](#8-vrf-design)
9. [Configuration Standards](#9-configuration-standards)
10. [Management & Monitoring](#10-management--monitoring)
11. [Security Design](#11-security-design)
12. [Automation Framework](#12-automation-framework)
13. [Appendix](#13-appendix)

---

## 1. Executive Summary

### 1.1 Purpose

This document defines the network architecture for E-University, a multi-campus educational institution requiring high-availability, secure, and segmented network services across three campuses:

- **Main Campus** - Primary academic and administrative facilities
- **Medical Campus** - Healthcare and medical research facilities (HIPAA compliant)
- **Research Campus** - Scientific research and partner collaboration

### 1.2 Design Goals

| Goal | Description |
|------|-------------|
| **High Availability** | Redundant core with no single point of failure |
| **Scalability** | Support for 100+ future nodes |
| **Segmentation** | VRF-based isolation for different user populations |
| **Security** | HIPAA compliance for medical, research isolation |
| **Automation** | NetBox + pyATS for configuration management |

### 1.3 Technologies Employed

- **OSPF** - IGP for underlay reachability
- **BGP** - iBGP with Route Reflectors for overlay
- **MPLS** - Label switching for traffic engineering
- **L3VPN** - VRF-based customer segmentation
- **BFD** - Fast failure detection (future)

---

## 2. Network Architecture Overview

### 2.1 Hierarchical Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET EDGE                                  │
│                     EUNIV-INET-GW1    EUNIV-INET-GW2                       │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┴───────────────────────────────────────────┐
│                              CORE LAYER                                     │
│           EUNIV-CORE1 ─── EUNIV-CORE2 ─── EUNIV-CORE3                      │
│               │               │               │                             │
│           EUNIV-CORE5 ─────────────────── EUNIV-CORE4                      │
│                         (Ring Topology)                                     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┴───────────────────────────────────────────┐
│                          AGGREGATION LAYER                                  │
│         EUNIV-MAIN-AGG1      EUNIV-MED-AGG1       EUNIV-RES-AGG1           │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┴───────────────────────────────────────────┐
│                              PE/BNG LAYER                                   │
│      MAIN-PE1  MAIN-PE2    MED-PE1  MED-PE2     RES-PE1  RES-PE2           │
│         └────────┘            └────────┘           └────────┘               │
│          (HA Pair)             (HA Pair)            (HA Pair)               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Layer Functions

| Layer | Devices | Function |
|-------|---------|----------|
| **Internet Edge** | INET-GW1, INET-GW2 | External connectivity, DDoS protection |
| **Core** | CORE1-5 | High-speed backbone, Route Reflection |
| **Aggregation** | AGG1 (per campus) | Campus uplink aggregation |
| **PE/BNG** | PE1, PE2 (per campus) | Customer VRF termination, services |

---

## 3. Device Inventory

### 3.1 Complete Device List

| Hostname | Role | Loopback IP | Management IP | BGP ASN | Platform |
|----------|------|-------------|---------------|---------|----------|
| EUNIV-CORE1 | Core / Route Reflector | 10.255.0.1 | 192.168.68.200 | 65000 | CSR1000V |
| EUNIV-CORE2 | Core / Route Reflector | 10.255.0.2 | 192.168.68.202 | 65000 | CSR1000V |
| EUNIV-CORE3 | Core / P Router | 10.255.0.3 | 192.168.68.203 | 65000 | CSR1000V |
| EUNIV-CORE4 | Core / P Router | 10.255.0.4 | 192.168.68.204 | 65000 | CSR1000V |
| EUNIV-CORE5 | Core / Route Reflector | 10.255.0.5 | 192.168.68.205 | 65000 | CSR1000V |
| EUNIV-INET-GW1 | Internet Gateway | 10.255.0.101 | 192.168.68.206 | 65000 | CSR1000V |
| EUNIV-INET-GW2 | Internet Gateway | 10.255.0.102 | 192.168.68.207 | 65000 | CSR1000V |
| EUNIV-MAIN-AGG1 | Main Campus Aggregation | 10.255.1.1 | 192.168.68.208 | 65000 | CSR1000V |
| EUNIV-MAIN-PE1 | Main Campus PE/BNG | 10.255.1.11 | 192.168.68.209 | 65000 | CSR1000V |
| EUNIV-MAIN-PE2 | Main Campus PE/BNG | 10.255.1.12 | 192.168.68.210 | 65000 | CSR1000V |
| EUNIV-MED-AGG1 | Medical Campus Aggregation | 10.255.2.1 | 192.168.68.211 | 65000 | CSR1000V |
| EUNIV-MED-PE1 | Medical Campus PE/BNG | 10.255.2.11 | 192.168.68.212 | 65000 | CSR1000V |
| EUNIV-MED-PE2 | Medical Campus PE/BNG | 10.255.2.12 | 192.168.68.213 | 65000 | CSR1000V |
| EUNIV-RES-AGG1 | Research Campus Aggregation | 10.255.3.1 | 192.168.68.214 | 65000 | CSR1000V |
| EUNIV-RES-PE1 | Research Campus PE/BNG | 10.255.3.11 | 192.168.68.215 | 65000 | CSR1000V |
| EUNIV-RES-PE2 | Research Campus PE/BNG | 10.255.3.12 | 192.168.68.216 | 65000 | CSR1000V |

### 3.2 Device Counts by Role

| Role | Count |
|------|-------|
| Core Routers | 5 |
| Internet Gateways | 2 |
| Aggregation Routers | 3 |
| PE/BNG Routers | 6 |
| **Total** | **16** |

---

## 4. Physical Topology

### 4.1 Core Ring Topology

```
                    EUNIV-CORE1 ◄────────────► EUNIV-CORE2
                     (RR)  │                      │  (RR)
                      Gi3  │                      │  Gi3
                           │                      │
                      Gi2  │                      │  Gi2
                           ▼                      ▼
                    EUNIV-CORE5 ◄────────────► EUNIV-CORE3
                     (RR)  │         Gi3          │
                      Gi2  │                      │  Gi3
                           │                      │
                           └──────► EUNIV-CORE4 ◄─┘
                                   Gi2      Gi3
```

### 4.2 Complete Cabling Table

#### Core Ring Links

| Cable | Device A | Port A | Device B | Port B | Subnet |
|-------|----------|--------|----------|--------|--------|
| 1 | EUNIV-CORE1 | Gi2 | EUNIV-CORE2 | Gi2 | 10.0.0.0/30 |
| 2 | EUNIV-CORE2 | Gi3 | EUNIV-CORE3 | Gi2 | 10.0.0.4/30 |
| 3 | EUNIV-CORE3 | Gi3 | EUNIV-CORE4 | Gi2 | 10.0.0.8/30 |
| 4 | EUNIV-CORE4 | Gi3 | EUNIV-CORE5 | Gi2 | 10.0.0.12/30 |
| 5 | EUNIV-CORE5 | Gi3 | EUNIV-CORE1 | Gi3 | 10.0.0.16/30 |

#### Internet Gateway Links

| Cable | Device A | Port A | Device B | Port B | Subnet |
|-------|----------|--------|----------|--------|--------|
| 6 | EUNIV-CORE1 | Gi4 | EUNIV-INET-GW1 | Gi2 | 10.0.0.20/30 |
| 7 | EUNIV-CORE2 | Gi4 | EUNIV-INET-GW2 | Gi2 | 10.0.0.24/30 |

#### Main Campus Links

| Cable | Device A | Port A | Device B | Port B | Subnet |
|-------|----------|--------|----------|--------|--------|
| 8 | EUNIV-CORE1 | Gi5 | EUNIV-MAIN-AGG1 | Gi2 | 10.0.1.0/30 |
| 9 | EUNIV-CORE2 | Gi5 | EUNIV-MAIN-AGG1 | Gi3 | 10.0.1.4/30 |
| 10 | EUNIV-MAIN-AGG1 | Gi4 | EUNIV-MAIN-PE1 | Gi2 | 10.0.1.8/30 |
| 11 | EUNIV-MAIN-AGG1 | Gi5 | EUNIV-MAIN-PE2 | Gi2 | 10.0.1.12/30 |
| 12 | EUNIV-MAIN-PE1 | Gi3 | EUNIV-MAIN-PE2 | Gi3 | 10.0.1.16/30 |

#### Medical Campus Links

| Cable | Device A | Port A | Device B | Port B | Subnet |
|-------|----------|--------|----------|--------|--------|
| 13 | EUNIV-CORE2 | Gi6 | EUNIV-MED-AGG1 | Gi2 | 10.0.2.0/30 |
| 14 | EUNIV-CORE3 | Gi4 | EUNIV-MED-AGG1 | Gi3 | 10.0.2.4/30 |
| 15 | EUNIV-MED-AGG1 | Gi4 | EUNIV-MED-PE1 | Gi2 | 10.0.2.8/30 |
| 16 | EUNIV-MED-AGG1 | Gi5 | EUNIV-MED-PE2 | Gi2 | 10.0.2.12/30 |
| 17 | EUNIV-MED-PE1 | Gi3 | EUNIV-MED-PE2 | Gi3 | 10.0.2.16/30 |

#### Research Campus Links

| Cable | Device A | Port A | Device B | Port B | Subnet |
|-------|----------|--------|----------|--------|--------|
| 18 | EUNIV-CORE4 | Gi4 | EUNIV-RES-AGG1 | Gi2 | 10.0.3.0/30 |
| 19 | EUNIV-CORE5 | Gi4 | EUNIV-RES-AGG1 | Gi3 | 10.0.3.4/30 |
| 20 | EUNIV-RES-AGG1 | Gi4 | EUNIV-RES-PE1 | Gi2 | 10.0.3.8/30 |
| 21 | EUNIV-RES-AGG1 | Gi5 | EUNIV-RES-PE2 | Gi2 | 10.0.3.12/30 |
| 22 | EUNIV-RES-PE1 | Gi3 | EUNIV-RES-PE2 | Gi3 | 10.0.3.16/30 |

**Total Physical Links: 22**

---

## 5. IP Addressing Plan

### 5.1 Address Block Allocation

| Block | Purpose | Size |
|-------|---------|------|
| 10.255.0.0/16 | Loopback addresses | /16 |
| 10.0.0.0/16 | Point-to-point links | /16 |
| 192.168.68.0/22 | Management network | /22 |
| 100.64.0.0/16 | CGNAT inside pool | /16 |
| 198.51.100.0/24 | CGNAT outside pool | /24 |

### 5.2 Loopback Addressing Scheme

| Range | Purpose |
|-------|---------|
| 10.255.0.1 - 10.255.0.5 | Core routers |
| 10.255.0.101 - 10.255.0.102 | Internet gateways |
| 10.255.1.0/24 | Main campus devices |
| 10.255.2.0/24 | Medical campus devices |
| 10.255.3.0/24 | Research campus devices |

### 5.3 Point-to-Point Link Addressing

| Range | Purpose |
|-------|---------|
| 10.0.0.0/24 | Core ring & gateway links |
| 10.0.1.0/24 | Main campus links |
| 10.0.2.0/24 | Medical campus links |
| 10.0.3.0/24 | Research campus links |

### 5.4 Management IP Assignments

| Device | Management IP |
|--------|---------------|
| EUNIV-CORE1 | 192.168.68.200/22 |
| EUNIV-CORE2 | 192.168.68.202/22 |
| EUNIV-CORE3 | 192.168.68.203/22 |
| EUNIV-CORE4 | 192.168.68.204/22 |
| EUNIV-CORE5 | 192.168.68.205/22 |
| EUNIV-INET-GW1 | 192.168.68.206/22 |
| EUNIV-INET-GW2 | 192.168.68.207/22 |
| EUNIV-MAIN-AGG1 | 192.168.68.208/22 |
| EUNIV-MAIN-PE1 | 192.168.68.209/22 |
| EUNIV-MAIN-PE2 | 192.168.68.210/22 |
| EUNIV-MED-AGG1 | 192.168.68.211/22 |
| EUNIV-MED-PE1 | 192.168.68.212/22 |
| EUNIV-MED-PE2 | 192.168.68.213/22 |
| EUNIV-RES-AGG1 | 192.168.68.214/22 |
| EUNIV-RES-PE1 | 192.168.68.215/22 |
| EUNIV-RES-PE2 | 192.168.68.216/22 |

---

## 6. Routing Design

### 6.1 OSPF Configuration

| Parameter | Value |
|-----------|-------|
| Process ID | 1 |
| Area | 0 (Backbone) |
| Router-ID | Loopback0 IP |
| Reference Bandwidth | 100000 Mbps |
| Network Type | Point-to-Point (on P2P links) |
| Passive Interfaces | Loopback0, GigabitEthernet1 |

#### OSPF Adjacency Summary

| Device | Expected Neighbors |
|--------|-------------------|
| CORE1 | CORE2, CORE5, INET-GW1, MAIN-AGG1 |
| CORE2 | CORE1, CORE3, INET-GW2, MAIN-AGG1, MED-AGG1 |
| CORE3 | CORE2, CORE4, MED-AGG1 |
| CORE4 | CORE3, CORE5, RES-AGG1 |
| CORE5 | CORE4, CORE1, RES-AGG1 |

### 6.2 BGP Configuration

| Parameter | Value |
|-----------|-------|
| AS Number | 65000 |
| Router-ID | Loopback0 IP |
| Update Source | Loopback0 |
| Address Families | IPv4 Unicast, VPNv4 |

#### Route Reflector Design

```
                    ┌─────────────────────────────────────┐
                    │         Route Reflector Mesh        │
                    │                                     │
                    │   CORE1 ◄────────────► CORE2       │
                    │   (RR)                   (RR)       │
                    │     │                     │         │
                    │     └────► CORE5 ◄────────┘         │
                    │            (RR)                     │
                    │    Cluster-ID: 10.255.0.12          │
                    │    Cluster-ID: 10.255.0.5           │
                    └─────────────────────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────────┐
                    │         Route Reflector Clients     │
                    │                                     │
                    │  CORE3, CORE4 (P Routers)          │
                    │  INET-GW1, INET-GW2                 │
                    │  MAIN-AGG1, MED-AGG1, RES-AGG1     │
                    │  All PE Routers                     │
                    └─────────────────────────────────────┘
```

| Route Reflector | Cluster-ID | Clients |
|-----------------|------------|---------|
| CORE1, CORE2 | 10.255.0.12 | All core, gateway, main/med devices |
| CORE5 | 10.255.0.5 | CORE3, CORE4, RES campus devices |

#### BGP Neighbor Summary by Device

| Device | BGP Neighbors |
|--------|---------------|
| CORE1 (RR) | CORE2, CORE3, CORE4, CORE5, INET-GW1, MAIN-AGG1 |
| CORE2 (RR) | CORE1, CORE3, CORE4, CORE5, INET-GW2, MAIN-AGG1, MED-AGG1 |
| CORE3 | CORE1, CORE2 (to RRs only) |
| CORE4 | CORE1, CORE5 (to RRs only) |
| CORE5 (RR) | CORE1, CORE2, CORE3, CORE4, RES-AGG1 |
| INET-GW1 | CORE1, CORE2 |
| INET-GW2 | CORE1, CORE2 |
| MAIN-AGG1 | CORE1, CORE2, MAIN-PE1, MAIN-PE2 |
| MAIN-PE1 | MAIN-AGG1 |
| MAIN-PE2 | MAIN-AGG1 |
| MED-AGG1 | CORE1, CORE2, MED-PE1, MED-PE2 |
| MED-PE1 | MED-AGG1 |
| MED-PE2 | MED-AGG1 |
| RES-AGG1 | CORE1, CORE5, RES-PE1, RES-PE2 |
| RES-PE1 | RES-AGG1 |
| RES-PE2 | RES-AGG1 |

---

## 7. MPLS Design

### 7.1 MPLS LDP Configuration

| Parameter | Value |
|-----------|-------|
| Label Protocol | LDP |
| Router-ID | Loopback0 (forced) |
| Label Range | Default |

#### MPLS-Enabled Interfaces

All point-to-point interfaces (Gi2-Gi6) on core, aggregation, and PE routers have MPLS enabled:

```
interface GigabitEthernet2
 mpls ip
```

### 7.2 Expected LDP Neighbors

| Device | LDP Neighbors |
|--------|---------------|
| CORE1 | CORE2, CORE5, INET-GW1, MAIN-AGG1 |
| CORE2 | CORE1, CORE3, INET-GW2, MAIN-AGG1, MED-AGG1 |
| CORE3 | CORE2, CORE4, MED-AGG1 |
| CORE4 | CORE3, CORE5, RES-AGG1 |
| CORE5 | CORE1, CORE4, RES-AGG1 |

---

## 8. VRF Design

### 8.1 VRF Definitions

| VRF Name | RD Suffix | Route Target | Purpose | Deployed On |
|----------|-----------|--------------|---------|-------------|
| STUDENT-NET | :100 | 65000:100 | Student residential | Main PE1/PE2 |
| STAFF-NET | :200 | 65000:200 | Staff/Faculty | All PEs |
| RESEARCH-NET | :300 | 65000:300 | Research partners | All PEs |
| MEDICAL-NET | :400 | 65000:400 | HIPAA medical | Med PE1/PE2 only |
| GUEST-NET | :500 | 65000:500 | Guest/Visitor | All PEs |

### 8.2 VRF Deployment Matrix

| VRF | MAIN-PE1 | MAIN-PE2 | MED-PE1 | MED-PE2 | RES-PE1 | RES-PE2 |
|-----|----------|----------|---------|---------|---------|---------|
| STUDENT-NET | ✓ | ✓ | - | - | - | - |
| STAFF-NET | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| RESEARCH-NET | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MEDICAL-NET | - | - | ✓ | ✓ | - | - |
| GUEST-NET | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### 8.3 VRF Configuration Example

```
vrf definition STUDENT-NET
 description Student residential network
 rd 10.255.1.11:100
 !
 address-family ipv4
  route-target import 65000:100
  route-target export 65000:100
 exit-address-family
```

### 8.4 VRF Security Notes

- **MEDICAL-NET**: Isolated to Medical campus only. No route leaking permitted (HIPAA compliance)
- **STUDENT-NET**: CGNAT enabled for IPv4 address conservation
- **GUEST-NET**: Internet-only access, no internal resources

---

## 9. Configuration Standards

### 9.1 Base Configuration Template

All devices include these standard configurations:

```
! === Services ===
service timestamps debug datetime msec localtime show-timezone
service timestamps log datetime msec localtime show-timezone
service password-encryption

! === Credentials ===
enable secret <password>
username admin privilege 15 secret <password>

! === Domain & DNS ===
ip domain name euniv.edu
ip name-server 10.255.255.1 10.255.255.2

! === SSH ===
ip ssh version 2

! === NTP ===
ntp server 10.255.255.10
ntp server 10.255.255.11

! === Logging ===
logging buffered 65536 informational
logging console informational

! === SNMP ===
snmp-server community euniv-mon-ro RO
snmp-server location E University Data Center
snmp-server contact noc@euniv.edu
```

### 9.2 Interface Naming Convention

| Interface | Purpose |
|-----------|---------|
| GigabitEthernet1 | Management (OOB) |
| GigabitEthernet2-6 | Core/Uplink connections |
| Loopback0 | Router-ID, BGP source |

### 9.3 Description Standards

```
interface GigabitEthernet2
 description To EUNIV-CORE2
```

Format: `To <PEER-HOSTNAME>`

---

## 10. Management & Monitoring

### 10.1 Management Network

| Parameter | Value |
|-----------|-------|
| Network | 192.168.68.0/22 |
| Gateway | 192.168.68.1 |
| VLAN | Native (untagged) |

### 10.2 NTP Configuration

| Server | IP Address |
|--------|------------|
| Primary | 10.255.255.10 |
| Secondary | 10.255.255.11 |

### 10.3 SNMP Configuration

| Parameter | Value |
|-----------|-------|
| Community (RO) | euniv-mon-ro |
| Location | E University Data Center |
| Contact | noc@euniv.edu |

### 10.4 Syslog Configuration

| Parameter | Value |
|-----------|-------|
| Buffer Size | 65536 |
| Level | Informational |

---

## 11. Security Design

### 11.1 VTY Access Control

```
ip access-list standard VTY-ACCESS
 permit 10.0.0.0 0.255.255.255
 permit 192.168.68.0 0.0.3.255
 deny any log
!
line vty 0 15
 access-class VTY-ACCESS in
 login local
 transport input ssh
 exec-timeout 30 0
```

### 11.2 Credential Management

| Account | Purpose | Privilege |
|---------|---------|-----------|
| admin | Primary admin account | 15 |

### 11.3 SSH Configuration

- SSH Version 2 only
- RSA key: 2048 bits
- VTY timeout: 30 minutes

---

## 12. Automation Framework

### 12.1 Source of Truth

**NetBox** (Cloud-hosted)
- URL: https://<your-netbox-website-address>
- Contains: Device inventory, IPs, connections, custom fields

### 12.2 Configuration Pipeline

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  NetBox  │ ──▶ │  Jinja2  │ ──▶ │  pyATS   │ ──▶ │  Device  │
│  (SoT)   │     │ Templates│     │  Deploy  │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

### 12.3 Automation Scripts

| Script | Purpose |
|--------|---------|
| `generate_configs.py` | Generate configs from templates |
| `validate.py` | Pre/post deployment validation |
| `deploy.py` | Deploy configs with backup/rollback |
| `orchestrate.py` | Full pipeline orchestration |

### 12.4 Validation Tests

| Test | Description |
|------|-------------|
| Connectivity | SSH reachability to all devices |
| Interfaces | Configured interfaces up/up |
| OSPF | All expected neighbors in FULL state |
| BGP | All sessions Established |
| MPLS LDP | All LDP neighbors Operational |

---

## 13. Appendix

### 13.1 Verification Commands

```bash
# OSPF
show ip ospf neighbor
show ip ospf interface brief
show ip route ospf

# BGP
show ip bgp summary
show ip bgp vpnv4 all summary
show ip bgp neighbors

# MPLS
show mpls ldp neighbor
show mpls forwarding-table
show mpls ldp bindings

# VRF
show vrf
show ip route vrf <name>
```

### 13.2 Troubleshooting Checklist

1. **No OSPF Neighbors**
   - Check physical connectivity
   - Verify IP addressing
   - Confirm OSPF process/area config

2. **BGP Not Established**
   - Verify OSPF for loopback reachability
   - Check update-source configuration
   - Confirm AS numbers

3. **No MPLS Labels**
   - Verify `mpls ip` on interfaces
   - Check LDP neighbor status
   - Confirm loopback in OSPF

### 13.3 Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-27 | Network Team | Initial release |

---

**End of Document**
