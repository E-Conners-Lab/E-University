
# E-University Network Design Document

**Document Version:** 3.1
**Date:** December 7, 2025
**Author:** Network Engineering Team
**Classification:** Internal Use

---

## Table of Contents

- [Quick Start](#quick-start)
1. [Executive Summary](#1-executive-summary)
2. [Network Architecture Overview](#2-network-architecture-overview)
3. [Device Inventory](#3-device-inventory)
4. [Physical Topology](#4-physical-topology)
5. [IP Addressing Plan](#5-ip-addressing-plan)
6. [Routing Design](#6-routing-design)
7. [MPLS Design](#7-mpls-design)
8. [VRF Design](#8-vrf-design)
9. [Layer 2 Security](#9-layer-2-security)
10. [Quality of Service (QoS)](#10-quality-of-service-qos)
11. [Configuration Standards](#11-configuration-standards)
12. [Management & Monitoring](#12-management--monitoring)
13. [Streaming Telemetry](#13-streaming-telemetry)
14. [Security Design](#14-security-design)
15. [Automation Framework](#15-automation-framework)
16. [Appendix](#16-appendix)

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **EVE-NG or GNS3** with the lab topology running
- Network devices accessible via SSH on the management network (192.168.68.0/22)

### Installation

```bash
# Clone the repository
git clone https://github.com/E-Conners-Lab/E-University.git
cd E-University

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
# Required: DEVICE_USERNAME, DEVICE_PASSWORD, DEVICE_ENABLE_PASSWORD
```

### Verify Connectivity

```bash
# Test device connectivity with pyATS
python -c "from pyats.topology import loader; tb = loader.load('testbed.yaml'); print('Testbed loaded:', tb.name)"

# Run L3VPN verification
python verify_l3vpn.py

# Run BFD verification
python verify_bfd.py
```

### Project Structure

```
.
├── configs/              # Generated device configurations
├── eve-ng/               # EVE-NG lab files
├── netbox/               # NetBox integration scripts
├── pyats/                # pyATS test jobs and scripts
├── scripts/              # Utility and automation scripts
├── telemetry/            # Streaming telemetry stack (TIG)
├── templates/            # Jinja2 configuration templates
├── testbed.yaml          # pyATS device inventory
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── deploy_*.py           # Deployment scripts
├── verify_*.py           # Verification scripts
└── traffic_test*.py      # Traffic testing scripts
```

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
- **BFD** - Fast failure detection (300ms) on edge links (Core↔INET-GW, AGG↔Edge)

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
│                              EDGE LAYER                                     │
│    MAIN-EDGE1 MAIN-EDGE2  MED-EDGE1 MED-EDGE2   RES-EDGE1 RES-EDGE2        │
│         └────────┘            └────────┘           └────────┘               │
│          (HA Pair)             (HA Pair)            (HA Pair)               │
├─────────────────────────────────────────────────────────────────────────────┤
│                              HOST LAYER                                     │
│       HOST1    HOST2       HOST3    HOST4        HOST5    HOST6            │
│      (Student)(Staff)    (Student)(Staff)      (Student)(Staff)            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Layer Functions

| Layer | Devices | Function |
|-------|---------|----------|
| **Internet Edge** | INET-GW1, INET-GW2 | External connectivity, DDoS protection |
| **Core** | CORE1-5 | High-speed backbone, Route Reflection |
| **Aggregation** | AGG1 (per campus) | Campus uplink aggregation |
| **Edge** | EDGE1, EDGE2 (per campus) | Customer VRF termination, services |
| **Host** | HOST1-6 | End-user traffic generation |

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
| EUNIV-MAIN-EDGE1 | Main Campus Edge | 10.255.1.11 | 192.168.68.209 | 65000 | CSR1000V |
| EUNIV-MAIN-EDGE2 | Main Campus Edge | 10.255.1.12 | 192.168.68.210 | 65000 | CSR1000V |
| EUNIV-MED-AGG1 | Medical Campus Aggregation | 10.255.2.1 | 192.168.68.211 | 65000 | CSR1000V |
| EUNIV-MED-EDGE1 | Medical Campus Edge | 10.255.2.11 | 192.168.68.212 | 65000 | CSR1000V |
| EUNIV-MED-EDGE2 | Medical Campus Edge | 10.255.2.12 | 192.168.68.213 | 65000 | CSR1000V |
| EUNIV-RES-AGG1 | Research Campus Aggregation | 10.255.3.1 | 192.168.68.214 | 65000 | CSR1000V |
| EUNIV-RES-EDGE1 | Research Campus Edge | 10.255.3.11 | 192.168.68.215 | 65000 | CSR1000V |
| EUNIV-RES-EDGE2 | Research Campus Edge | 10.255.3.12 | 192.168.68.216 | 65000 | CSR1000V |
| EUNIV-MED-ASW1 | Medical Campus Access Switch | N/A | 192.168.68.217 | N/A | Cat9kv |

### 3.2 Host Router Inventory

| Hostname | Role | Host IP | Gateway | Management IP | Connected To | Platform |
|----------|------|---------|---------|---------------|--------------|----------|
| HOST1 | Traffic Generator | 172.18.1.10 | 172.18.1.1 | 192.168.68.55 | RES-EDGE1 Gi6 | IOSv |
| HOST2 | Traffic Generator | 172.18.2.10 | 172.18.2.1 | 192.168.68.74 | RES-EDGE2 Gi6 | IOSv |
| HOST3 | Traffic Generator | 172.16.1.10 | 172.16.1.1 | 192.168.68.77 | MAIN-EDGE1 Gi4 | IOSv |
| HOST4 | Traffic Generator | 172.16.2.10 | 172.16.2.1 | 192.168.68.78 | MAIN-EDGE2 Gi6 | IOSv |
| HOST5 | Traffic Generator | 172.17.2.10 | 172.17.2.1 | 192.168.68.79 | MED-EDGE2 Gi6 | IOSv |
| HOST6 | Traffic Generator | 172.17.1.10 | 172.17.1.1 | 192.168.68.80 | MED-EDGE1 Gi6 | IOSv |

### 3.3 Device Counts by Role

| Role | Count |
|------|-------|
| Core Routers | 5 |
| Internet Gateways | 2 |
| Aggregation Routers | 3 |
| Edge Routers | 6 |
| Host Routers | 6 |
| **Total** | **22** |

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
| 10 | EUNIV-MAIN-AGG1 | Gi4 | EUNIV-MAIN-EDGE1 | Gi2 | 10.0.1.8/30 |
| 11 | EUNIV-MAIN-AGG1 | Gi5 | EUNIV-MAIN-EDGE2 | Gi2 | 10.0.1.12/30 |
| 12 | EUNIV-MAIN-EDGE1 | Gi3 | EUNIV-MAIN-EDGE2 | Gi3 | 10.0.1.16/30 |

#### Medical Campus Links

| Cable | Device A | Port A | Device B | Port B | Subnet |
|-------|----------|--------|----------|--------|--------|
| 13 | EUNIV-CORE2 | Gi6 | EUNIV-MED-AGG1 | Gi2 | 10.0.2.0/30 |
| 14 | EUNIV-CORE3 | Gi4 | EUNIV-MED-AGG1 | Gi3 | 10.0.2.4/30 |
| 15 | EUNIV-MED-AGG1 | Gi4 | EUNIV-MED-EDGE1 | Gi2 | 10.0.2.8/30 |
| 16 | EUNIV-MED-AGG1 | Gi5 | EUNIV-MED-EDGE2 | Gi2 | 10.0.2.12/30 |
| 17 | EUNIV-MED-EDGE1 | Gi3 | EUNIV-MED-EDGE2 | Gi3 | 10.0.2.16/30 |

#### Research Campus Links

| Cable | Device A | Port A | Device B | Port B | Subnet |
|-------|----------|--------|----------|--------|--------|
| 18 | EUNIV-CORE4 | Gi4 | EUNIV-RES-AGG1 | Gi2 | 10.0.3.0/30 |
| 19 | EUNIV-CORE5 | Gi4 | EUNIV-RES-AGG1 | Gi3 | 10.0.3.4/30 |
| 20 | EUNIV-RES-AGG1 | Gi4 | EUNIV-RES-EDGE1 | Gi2 | 10.0.3.8/30 |
| 21 | EUNIV-RES-AGG1 | Gi5 | EUNIV-RES-EDGE2 | Gi2 | 10.0.3.12/30 |
| 22 | EUNIV-RES-EDGE1 | Gi3 | EUNIV-RES-EDGE2 | Gi3 | 10.0.3.16/30 |

#### Host Links (IOSv Routers)

| Cable | Device A | Port A | Device B | Port B | Subnet | VRF |
|-------|----------|--------|----------|--------|--------|-----|
| 23 | EUNIV-RES-EDGE1 | Gi6 | HOST1 | Gi0/0 | 172.18.1.0/24 | STAFF-NET |
| 24 | EUNIV-RES-EDGE2 | Gi6 | HOST2 | Gi0/0 | 172.18.2.0/24 | STAFF-NET |
| 25 | EUNIV-MAIN-EDGE1 | Gi4 | HOST3 | Gi0/2 | 172.16.1.0/24 | STAFF-NET |
| 26 | EUNIV-MAIN-EDGE2 | Gi6 | HOST4 | Gi0/0 | 172.16.2.0/24 | STAFF-NET |
| 27 | EUNIV-MED-EDGE2 | Gi6 | HOST5 | Gi0/0 | 172.17.2.0/24 | STAFF-NET |
| 28 | EUNIV-MED-EDGE1 | Gi6 | HOST6 | Gi0/0 | 172.17.1.0/24 | STAFF-NET |

**Total Physical Links: 28**

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
| EUNIV-MAIN-EDGE1 | 192.168.68.209/22 |
| EUNIV-MAIN-EDGE2 | 192.168.68.210/22 |
| EUNIV-MED-AGG1 | 192.168.68.211/22 |
| EUNIV-MED-EDGE1 | 192.168.68.212/22 |
| EUNIV-MED-EDGE2 | 192.168.68.213/22 |
| EUNIV-RES-AGG1 | 192.168.68.214/22 |
| EUNIV-RES-EDGE1 | 192.168.68.215/22 |
| EUNIV-RES-EDGE2 | 192.168.68.216/22 |

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
                    │  All Edge Routers                   │
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
| MAIN-AGG1 | CORE1, CORE2, MAIN-EDGE1, MAIN-EDGE2 |
| MAIN-EDGE1 | MAIN-AGG1 |
| MAIN-EDGE2 | MAIN-AGG1 |
| MED-AGG1 | CORE1, CORE2, MED-EDGE1, MED-EDGE2 |
| MED-EDGE1 | MED-AGG1 |
| MED-EDGE2 | MED-AGG1 |
| RES-AGG1 | CORE1, CORE5, RES-EDGE1, RES-EDGE2 |
| RES-EDGE1 | RES-AGG1 |
| RES-EDGE2 | RES-AGG1 |

---

## 7. MPLS Design

### 7.1 MPLS LDP Configuration

| Parameter | Value |
|-----------|-------|
| Label Protocol | LDP |
| Router-ID | Loopback0 (forced) |
| Label Range | Default |

#### MPLS-Enabled Interfaces

All point-to-point interfaces (Gi2-Gi6) on core, aggregation, and Edge routers have MPLS enabled:

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

### 7.3 BFD Design

BFD (Bidirectional Forwarding Detection) is deployed on **edge links only** - not inside the MPLS core where IGP convergence is sufficient.

#### BFD Parameters

| Parameter | Value |
|-----------|-------|
| Interval | 100ms |
| Min RX | 100ms |
| Multiplier | 3 |
| Detection Time | 300ms |

#### BFD-Enabled Links

| Link Type | Device A | Interface | Device B | Interface |
|-----------|----------|-----------|----------|-----------|
| Core↔INET-GW | EUNIV-CORE1 | Gi4 | EUNIV-INET-GW1 | Gi2 |
| Core↔INET-GW | EUNIV-CORE2 | Gi4 | EUNIV-INET-GW2 | Gi2 |
| AGG↔Edge | EUNIV-MAIN-AGG1 | Gi4 | EUNIV-MAIN-EDGE1 | Gi2 |
| AGG↔Edge | EUNIV-MAIN-AGG1 | Gi5 | EUNIV-MAIN-EDGE2 | Gi2 |
| AGG↔Edge | EUNIV-MED-AGG1 | Gi4 | EUNIV-MED-EDGE1 | Gi2 |
| AGG↔Edge | EUNIV-MED-AGG1 | Gi5 | EUNIV-MED-EDGE2 | Gi2 |
| AGG↔Edge | EUNIV-RES-AGG1 | Gi4 | EUNIV-RES-EDGE1 | Gi2 |
| AGG↔Edge | EUNIV-RES-AGG1 | Gi5 | EUNIV-RES-EDGE2 | Gi2 |

#### BFD Configuration Example

```
interface GigabitEthernet4
 bfd interval 100 min_rx 100 multiplier 3

router ospf 1
 bfd all-interfaces
```

#### Why Not BFD in the Core?

- MPLS core has multiple redundant paths
- OSPF fast-hello (1s dead-timer) provides sufficient convergence
- LDP converges based on IGP - no additional benefit from BFD
- Reduces operational complexity and CPU overhead

BFD is most valuable at network edges where:
1. **INET-GW links** - Fast detection of upstream ISP failures
2. **AGG↔Edge links** - Fast PE failover for customer VRFs

### 7.4 HSRP High Availability Design

HSRP (Hot Standby Router Protocol) provides gateway redundancy for customer-facing VRF interfaces on PE router pairs.

#### HSRP Implementation

HSRP runs on **GigabitEthernet3 subinterfaces** - the existing inter-PE link. Using dot1q encapsulation, HSRP traffic rides over the same physical link that carries native routed OSPF/MPLS traffic. This eliminates the need for an additional L2 switch between PE pairs.

#### HSRP Parameters

| Parameter | Value |
|-----------|-------|
| Interface | GigabitEthernet3.{vlan} |
| Version | HSRPv2 |
| Hello Timer | 1 second |
| Hold Timer | 3 seconds |
| Preempt Delay | 30 seconds |

#### HSRP Load Balancing Strategy

Traffic is distributed across EDGE1 and EDGE2 by assigning different active routers per VLAN:

| VLANs | Active Router | Priority |
|-------|---------------|----------|
| 100 (STUDENT), 300 (RESEARCH) | EDGE1 | 150 |
| 200 (STAFF), 400 (MEDICAL), 500 (GUEST) | EDGE2 | 150 |

Standby routers use priority 100 and preempt after 30 seconds.

#### HSRP Groups by Campus (11 total)

**Main Campus** - IP scheme: `10.{vlan/10}.1.x`
| VLAN | VRF | EDGE1 IP | EDGE2 IP | Virtual IP | Active |
|------|-----|----------|----------|------------|--------|
| 100 | STUDENT-NET | 10.10.1.1 | 10.10.1.2 | 10.10.1.254 | EDGE1 |
| 200 | STAFF-NET | 10.20.1.1 | 10.20.1.2 | 10.20.1.254 | EDGE2 |
| 300 | RESEARCH-NET | 10.30.1.1 | 10.30.1.2 | 10.30.1.254 | EDGE1 |
| 500 | GUEST-NET | 10.50.1.1 | 10.50.1.2 | 10.50.1.254 | EDGE2 |

**Medical Campus** - IP scheme: `10.{vlan/10}.2.x`
| VLAN | VRF | EDGE1 IP | EDGE2 IP | Virtual IP | Active |
|------|-----|----------|----------|------------|--------|
| 200 | STAFF-NET | 10.20.2.1 | 10.20.2.2 | 10.20.2.254 | EDGE2 |
| 300 | RESEARCH-NET | 10.30.2.1 | 10.30.2.2 | 10.30.2.254 | EDGE1 |
| 400 | MEDICAL-NET | 10.40.2.1 | 10.40.2.2 | 10.40.2.254 | EDGE2 |
| 500 | GUEST-NET | 10.50.2.1 | 10.50.2.2 | 10.50.2.254 | EDGE2 |

**Research Campus** - IP scheme: `10.{vlan/10}.3.x`
| VLAN | VRF | EDGE1 IP | EDGE2 IP | Virtual IP | Active |
|------|-----|----------|----------|------------|--------|
| 200 | STAFF-NET | 10.20.3.1 | 10.20.3.2 | 10.20.3.254 | EDGE2 |
| 300 | RESEARCH-NET | 10.30.3.1 | 10.30.3.2 | 10.30.3.254 | EDGE1 |
| 500 | GUEST-NET | 10.50.3.1 | 10.50.3.2 | 10.50.3.254 | EDGE2 |

#### HSRP Configuration Example

```
interface GigabitEthernet3.200
 description STAFF-NET Gateway (HSRP with EUNIV-MAIN-PE2)
 encapsulation dot1Q 200
 vrf forwarding STAFF-NET
 ip address 10.100.2.2 255.255.255.0
 standby version 2
 standby 200 ip 10.100.2.1
 standby 200 priority 110
 standby 200 preempt delay minimum 30
 standby 200 timers 1 3
```

#### HSRP Verification Commands

```bash
# Show HSRP summary
show standby brief

# Show detailed HSRP status
show standby

# Show HSRP for specific interface
show standby GigabitEthernet3.200
```

#### How HSRP Works Over Gi3

The native Gi3 interface remains a routed OSPF/MPLS point-to-point link:
```
interface GigabitEthernet3
 ip address 10.0.2.17 255.255.255.252
 ip ospf network point-to-point
 ip ospf 1 area 0
 mpls ip
```

HSRP subinterfaces are added on top with dot1q tagging:
```
interface GigabitEthernet3.200   ! VLAN 200 for STAFF-NET
interface GigabitEthernet3.300   ! VLAN 300 for RESEARCH-NET
```

This allows both L3 routing (native) and L2 HSRP (tagged) to coexist on the same physical link.

---

## 8. VRF Design

### 8.1 VRF Definitions

| VRF Name | RD Suffix | Route Target | Purpose | Deployed On |
|----------|-----------|--------------|---------|-------------|
| STUDENT-NET | :100 | 65000:100 | Student residential | Main EDGE1/EDGE2 |
| STAFF-NET | :200 | 65000:200 | Staff/Faculty | All Edge routers |
| RESEARCH-NET | :300 | 65000:300 | Research partners | All Edge routers |
| MEDICAL-NET | :400 | 65000:400 | HIPAA medical | Med EDGE1/EDGE2 only |
| GUEST-NET | :500 | 65000:500 | Guest/Visitor | All Edge routers |

### 8.2 VRF Deployment Matrix

| VRF | MAIN-EDGE1 | MAIN-EDGE2 | MED-EDGE1 | MED-EDGE2 | RES-EDGE1 | RES-EDGE2 |
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

### 8.5 VRF Internet Access via INET-GW

VRF internet access is provided through a centralized design using the **INET-GW routers** as the single egress point for all VRF traffic. This architecture provides:
- Centralized NAT management on 2 routers instead of 6
- Proper MPLS L3VPN traffic flow through the core
- Consistent security policy enforcement at the edge

#### Architecture

```
                     ┌─────────────────────────────────────┐
                     │           INTERNET                  │
                     └───────────────┬─────────────────────┘
                                     │
                           ┌─────────┴─────────┐
                           │   INET-GW1/GW2    │
                           │   VRF-aware NAT   │
                           │   PAT on Gi1      │
                           └─────────┬─────────┘
                                     │ BGP VPNv4
                                     │ default-information originate
                           ┌─────────┴─────────┐
                           │     MPLS Core     │
                           │   (Label Switch)  │
                           └─────────┬─────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
   MAIN-EDGE1/2               MED-EDGE1/2                   RES-EDGE1/2
   (VRF learned                (VRF learned                (VRF learned
    0.0.0.0/0 via BGP)          0.0.0.0/0 via BGP)          0.0.0.0/0 via BGP)
```

#### INET-GW NAT Configuration

```
! NAT ACL covers all VRF prefixes
ip access-list standard VRF-NAT-ACL
 permit 10.1.0.0 0.0.255.255
 permit 10.2.0.0 0.0.255.255
 permit 10.3.0.0 0.0.255.255

! VRF-aware NAT for each VRF
ip nat inside source list VRF-NAT-ACL interface GigabitEthernet1 vrf STAFF-NET overload
ip nat inside source list VRF-NAT-ACL interface GigabitEthernet1 vrf RESEARCH-NET overload
ip nat inside source list VRF-NAT-ACL interface GigabitEthernet1 vrf MEDICAL-NET overload
ip nat inside source list VRF-NAT-ACL interface GigabitEthernet1 vrf GUEST-NET overload

! Static default route per VRF to gateway
ip route vrf STAFF-NET 0.0.0.0 0.0.0.0 192.168.68.1
ip route vrf RESEARCH-NET 0.0.0.0 0.0.0.0 192.168.68.1
ip route vrf MEDICAL-NET 0.0.0.0 0.0.0.0 192.168.68.1
ip route vrf GUEST-NET 0.0.0.0 0.0.0.0 192.168.68.1
```

#### BGP Default Route Origination

```
! On INET-GW1/GW2 - Advertise default to VRFs
router bgp 65000
 address-family ipv4 vrf STAFF-NET
  default-information originate
 address-family ipv4 vrf RESEARCH-NET
  default-information originate
 address-family ipv4 vrf MEDICAL-NET
  default-information originate
 address-family ipv4 vrf GUEST-NET
  default-information originate
```

#### Validation

```bash
# Verify NAT translations on INET-GW
show ip nat translations
show ip nat statistics

# Verify VRF default route learned on Edge routers
show ip route vrf STAFF-NET 0.0.0.0

# Test internet connectivity from Edge router
ping vrf STAFF-NET 8.8.8.8 source 10.1.10.2
```

### 8.6 Access Layer SVI Design

Edge routers provide Layer 3 gateway services for campus VLANs via **GigabitEthernet4 subinterfaces** with HSRP for gateway redundancy.

#### Architecture

```
                    EDGE1 ◄─── Gi3 (HSRP heartbeat) ───► EDGE2
                      │                                    │
                    Gi4.10 (VLAN 10)                   Gi4.10 (VLAN 10)
                    Gi4.20 (VLAN 20)                   Gi4.20 (VLAN 20)
                    Gi4.30 (VLAN 30)                   Gi4.30 (VLAN 30)
                    Gi4.40 (VLAN 40)                   Gi4.40 (VLAN 40)
                      │                                    │
                      └─────────► Access Switch ◄──────────┘
                                  (802.1Q trunk)
```

#### VLAN to VRF Mapping

| VLAN | Name | VRF | IP Range per Campus |
|------|------|-----|---------------------|
| 10 | STAFF | STAFF-NET | 10.{campus}.10.0/24 |
| 20 | RESEARCH | RESEARCH-NET | 10.{campus}.20.0/24 |
| 30 | MEDICAL | MEDICAL-NET | 10.{campus}.30.0/24 (Medical only) |
| 40 | GUEST | GUEST-NET | 10.{campus}.40.0/24 |

Campus codes: Main=1, Medical=2, Research=3

#### SVI Configuration with HSRP

```
! Main Campus EDGE1 - STAFF VLAN
interface GigabitEthernet4.10
 description STAFF VLAN Gateway
 encapsulation dot1Q 10
 vrf forwarding STAFF-NET
 ip address 10.1.10.2 255.255.255.0
 standby version 2
 standby 10 ip 10.1.10.1
 standby 10 priority 150
 standby 10 preempt delay minimum 30
 standby 10 timers 1 3

! Main Campus EDGE2 - STAFF VLAN (standby)
interface GigabitEthernet4.10
 description STAFF VLAN Gateway
 encapsulation dot1Q 10
 vrf forwarding STAFF-NET
 ip address 10.1.10.3 255.255.255.0
 standby version 2
 standby 10 ip 10.1.10.1
 standby 10 priority 100
 standby 10 preempt delay minimum 30
 standby 10 timers 1 3
```

#### HSRP Load Balancing

| VLANs | Active Router | Priority |
|-------|---------------|----------|
| 10 (STAFF), 30 (MEDICAL) | EDGE1 | 150 |
| 20 (RESEARCH), 40 (GUEST) | EDGE2 | 150 |

### 8.7 Centralized DHCP Services

DHCP services are provided by a centralized **dnsmasq server** running in Docker, with DHCP relay configured on Edge routers.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Docker Host (192.168.68.57)                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     dnsmasq container                        │   │
│  │   - DHCP server for all campus VLANs                        │   │
│  │   - DNS forwarder (8.8.8.8, 8.8.4.4)                        │   │
│  │   - Ports: UDP 67, 68                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ DHCP Relay
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
   MAIN-EDGE1/2               MED-EDGE1/2                RES-EDGE1/2
   ip helper-address          ip helper-address          ip helper-address
   192.168.68.57              192.168.68.57              192.168.68.57
```

#### DHCP Pool Definitions

| Campus | VLAN | Range | Lease | Domain |
|--------|------|-------|-------|--------|
| Main | 10 (STAFF) | 10.1.10.100-200 | 12h | staff.main.euniv.lab |
| Main | 20 (RESEARCH) | 10.1.20.100-200 | 12h | research.main.euniv.lab |
| Main | 40 (GUEST) | 10.1.40.100-200 | 2h | guest.main.euniv.lab |
| Medical | 10 (STAFF) | 10.2.10.100-200 | 12h | staff.medical.euniv.lab |
| Medical | 20 (RESEARCH) | 10.2.20.100-200 | 12h | research.medical.euniv.lab |
| Medical | 30 (MEDICAL) | 10.2.30.100-200 | 12h | medical.euniv.lab |
| Medical | 40 (GUEST) | 10.2.40.100-200 | 2h | guest.medical.euniv.lab |
| Research | 10 (STAFF) | 10.3.10.100-200 | 12h | staff.research.euniv.lab |
| Research | 20 (RESEARCH) | 10.3.20.100-200 | 12h | research.research.euniv.lab |
| Research | 40 (GUEST) | 10.3.40.100-200 | 2h | guest.research.euniv.lab |

#### Edge Router DHCP Relay Configuration

```
interface GigabitEthernet4.10
 ip helper-address 192.168.68.57
```

#### dnsmasq Configuration Location

Configuration file: `telemetry/dnsmasq/dnsmasq.conf`

```bash
# Start DHCP server
cd telemetry
docker compose up -d dnsmasq

# View DHCP logs
docker logs -f euniv-dhcp
```

---

## 9. Layer 2 Security

Enterprise-grade Layer 2 security is deployed on access switches to provide defense-in-depth at the network edge.

### 9.1 Access Switch Inventory

| Switch | Campus | Management IP | Platform | Uplinks |
|--------|--------|---------------|----------|---------|
| EUNIV-MED-ASW1 | Medical | 192.168.68.217 | Cat9kv | Gi1/0/1-2 to MED-EDGE1/2 |

### 9.2 VLAN Configuration

| VLAN ID | Name | Purpose | VRF |
|---------|------|---------|-----|
| 10 | STAFF | Staff and faculty | STAFF-NET |
| 20 | RESEARCH | Research partners | RESEARCH-NET |
| 30 | MEDICAL | HIPAA medical | MEDICAL-NET |
| 40 | GUEST | Guest/visitor | GUEST-NET |
| 99 | MGMT | Switch management | - |
| 100 | INFRA | Infrastructure (RADIUS) | - |

### 9.3 Security Features Deployed

| Feature | Purpose | Configuration |
|---------|---------|---------------|
| **802.1X** | Port-based authentication | RADIUS with dynamic VLAN assignment |
| **DHCP Snooping** | Prevent rogue DHCP servers | Enabled on VLANs 10, 20, 30, 40 |
| **Dynamic ARP Inspection** | Prevent ARP spoofing | Enabled on VLANs 10, 20, 30, 40 |
| **Port Security** | MAC address limits | Max 3 MACs, restrict violation |
| **BPDU Guard** | STP attack prevention | Enabled on access ports |
| **PortFast** | Fast edge port convergence | Enabled on access ports |
| **Storm Control** | Broadcast/multicast limiting | 10% threshold |
| **IP Source Guard** | IP spoofing prevention | Requires DHCP snooping binding |

### 9.4 Trunk Port Configuration

Uplink trunk ports (Gi1/0/1, Gi1/0/2) are configured with:
- Native VLAN 99 (non-default for security)
- Allowed VLANs: 10, 20, 30, 40, 99, 100
- DHCP Snooping trusted
- DAI trusted
- Root Guard enabled

### 9.5 Access Port Configuration

User-facing access ports are configured with:
- 802.1X authentication (ports 4-8)
- Port security with MAC limiting
- BPDU Guard / PortFast
- Storm control thresholds
- IP Source Guard

### 9.6 802.1X / RADIUS Configuration

```
aaa new-model
aaa authentication dot1x default group RADIUS-SERVERS
aaa authorization network default group RADIUS-SERVERS
dot1x system-auth-control

radius server EUNIV-RADIUS
  address ipv4 192.168.68.69 auth-port 1812 acct-port 1813
  key <secret>
```

RADIUS provides dynamic VLAN assignment based on user credentials:
- Staff users → VLAN 10
- Research users → VLAN 20
- Medical users → VLAN 30
- Guest users → VLAN 40

### 9.7 L2 Security Scripts

| Script | Purpose |
|--------|---------|
| `scripts/configure_l2_security.py` | Deploy L2 security config to access switches |
| `pyats/tests/test_l2_security.py` | Validate L2 security configuration (27 tests) |

**Usage:**
```bash
# Dry-run to preview configuration
python scripts/configure_l2_security.py --switch EUNIV-MED-ASW1 --dry-run

# Deploy configuration
python scripts/configure_l2_security.py --switch EUNIV-MED-ASW1

# Run validation tests
source .env
pytest pyats/tests/test_l2_security.py -v
```

### 9.8 Validation Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| VLAN Configuration | 2 | Verify VLANs exist with correct names |
| Trunk Configuration | 3 | Verify trunk mode, allowed VLANs, native VLAN |
| 802.1X Configuration | 6 | AAA, RADIUS, dot1x on access ports |
| DHCP Snooping | 3 | Global enable, VLAN config, trusted ports |
| Dynamic ARP Inspection | 2 | VLAN config, trusted ports |
| Port Security | 2 | Enabled status, MAC limits |
| STP Protection | 3 | BPDU Guard, PortFast, Root Guard |
| Storm Control | 2 | Configuration and thresholds |
| RADIUS Connectivity | 2 | Server reachability, AAA status |
| IP Source Guard | 1 | Configuration status |
| Security Baseline | 1 | Overall security posture |

---

## 10. Quality of Service (QoS)

Enterprise-class QoS is deployed on Edge routers to provide differentiated services for various traffic types across VRFs.

### 10.1 QoS Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              QoS Policy Flow                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Ingress (VRF interfaces)              Egress (WAN interfaces)              │
│  ┌─────────────────────┐               ┌─────────────────────┐              │
│  │  EUNIV-VRF-MARKING  │───────────────│  EUNIV-QOS-QUEUING  │              │
│  │                     │               │                     │              │
│  │  - Match VRF        │               │  - Priority Queue   │              │
│  │  - Set DSCP         │               │  - CBWFQ            │              │
│  │  - Mark traffic     │               │  - Fair Queue       │              │
│  └─────────────────────┘               └─────────────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Traffic Classification

Traffic is classified and marked based on VRF membership:

| VRF | Traffic Type | DSCP Value | PHB | Queue |
|-----|-------------|------------|-----|-------|
| MEDICAL-NET | Critical Healthcare | EF (46) | Expedited Forwarding | Priority (LLQ) |
| RESEARCH-NET | Research Data | AF31 (26) | Assured Forwarding 3 | Bandwidth 30% |
| STAFF-NET | Business Apps | AF21 (18) | Assured Forwarding 2 | Bandwidth 20% |
| GUEST-NET | Best Effort | CS1 (8) | Scavenger | Fair Queue |

### 10.3 Marking Policy (Ingress)

```
! Class definitions by VRF
class-map match-all MEDICAL-TRAFFIC
 match vrf MEDICAL-NET
class-map match-all RESEARCH-TRAFFIC
 match vrf RESEARCH-NET
class-map match-all STAFF-TRAFFIC
 match vrf STAFF-NET
class-map match-all GUEST-TRAFFIC
 match vrf GUEST-NET

! Marking policy
policy-map EUNIV-VRF-MARKING
 class MEDICAL-TRAFFIC
  set dscp ef
 class RESEARCH-TRAFFIC
  set dscp af31
 class STAFF-TRAFFIC
  set dscp af21
 class GUEST-TRAFFIC
  set dscp cs1
 class class-default
  set dscp default
```

### 10.4 Queuing Policy (Egress)

```
! Queuing classes
class-map match-any VOICE-VIDEO
 match dscp ef
 match dscp af41
class-map match-any CRITICAL-DATA
 match dscp af31
 match dscp af32
 match dscp af33
class-map match-any BUSINESS
 match dscp af21
 match dscp af22
 match dscp af23
class-map match-any SCAVENGER
 match dscp cs1

! Hierarchical queuing policy
policy-map EUNIV-QOS-QUEUING
 class VOICE-VIDEO
  priority percent 20
 class CRITICAL-DATA
  bandwidth percent 30
 class BUSINESS
  bandwidth percent 20
 class SCAVENGER
  bandwidth percent 5
  random-detect dscp-based
 class class-default
  fair-queue
```

### 10.5 Policy Application

```
! Apply to VRF subinterfaces (ingress marking)
interface GigabitEthernet4.10
 service-policy input EUNIV-VRF-MARKING

interface GigabitEthernet4.20
 service-policy input EUNIV-VRF-MARKING

interface GigabitEthernet4.30
 service-policy input EUNIV-VRF-MARKING

interface GigabitEthernet4.40
 service-policy input EUNIV-VRF-MARKING

! Apply to WAN interface (egress queuing)
interface GigabitEthernet2
 service-policy output EUNIV-QOS-QUEUING
```

### 10.6 QoS Validation

```bash
# Verify policy application
show policy-map interface GigabitEthernet4.10
show policy-map interface GigabitEthernet2

# Check DSCP counters
show policy-map interface GigabitEthernet4.10 | include packets

# Run pyATS QoS validation
cd pyats
pyats run job qos_job.py --testbed-file testbed.yaml
```

### 10.7 QoS Scripts

| Script | Purpose |
|--------|---------|
| `scripts/configure_qos.py` | Deploy QoS policies to Edge routers |
| `pyats/tests/qos_aetest.py` | Validate QoS configuration |
| `pyats/qos_job.py` | pyATS job for QoS testing |

---

## 11. Configuration Standards

### 11.1 Base Configuration Template

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

### 10.2 Interface Naming Convention

| Interface | Purpose |
|-----------|---------|
| GigabitEthernet1 | Management (OOB) |
| GigabitEthernet2-6 | Core/Uplink connections |
| Loopback0 | Router-ID, BGP source |

### 10.3 Description Standards

```
interface GigabitEthernet2
 description To EUNIV-CORE2
```

Format: `To <PEER-HOSTNAME>`

---

## 12. Management & Monitoring

### 12.1 Management Network

| Parameter | Value |
|-----------|-------|
| Network | 192.168.68.0/22 |
| Gateway | 192.168.68.1 |
| VLAN | Native (untagged) |

### 11.2 NTP Configuration

| Server | IP Address |
|--------|------------|
| Primary | 10.255.255.10 |
| Secondary | 10.255.255.11 |

### 11.3 SNMP Configuration

| Parameter | Value |
|-----------|-------|
| Community (RO) | euniv-mon-ro |
| Location | E University Data Center |
| Contact | noc@euniv.edu |

### 11.4 Syslog Configuration

| Parameter | Value |
|-----------|-------|
| Buffer Size | 65536 |
| Level | Informational |

---

## 13. Streaming Telemetry

Real-time network observability using a containerized telemetry stack.

### 13.1 Architecture

```
┌─────────────────┐    SSH/CLI     ┌─────────────────┐
│  Network        │◄──────────────►│   Collector     │
│  Devices (16)   │                │   (Python)      │
└─────────────────┘                └────────┬────────┘
                                           │
                                           ▼
                                  ┌─────────────────┐
                                  │   InfluxDB 2.x  │
                                  │   (Time-Series) │
                                  └────────┬────────┘
                                           │
                                           ▼
                                  ┌─────────────────┐
                                  │   Grafana       │
                                  │   (Dashboards)  │
                                  └─────────────────┘
```

### 12.2 Stack Components

| Component | Container | Port | Purpose |
|-----------|-----------|------|---------|
| **InfluxDB 2.7** | `euniv-influxdb` | 8086 | Time-series database |
| **Grafana 10.2** | `euniv-grafana` | 3001 | Visualization dashboards |
| **Collector** | `euniv-collector` | - | Python/Netmiko polling |

### 12.3 Metrics Collected

| Category | Metrics | Collection Interval |
|----------|---------|---------------------|
| **Device Health** | CPU (5s, 1m, 5m avg), Memory (%), Reachability | 30s |
| **Interface Stats** | Input/output packets, bit rates, errors | 30s |
| **OSPF** | Neighbor count, full adjacencies | 30s |
| **BGP** | Session state, prefix counts per neighbor | 30s |
| **BFD** | Sessions up/down count | 30s |
| **HSRP** | Active/Standby state per group (11 groups) | 30s |

### 12.4 Quick Start

```bash
cd telemetry

# First time - build and start
./start.sh --build

# Subsequent runs
./start.sh

# View collector logs
./start.sh --logs collector

# Stop everything
./start.sh --stop
```

### 12.5 Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3001 | See `telemetry/.env` |
| InfluxDB | http://localhost:8086 | See `telemetry/.env` |

### 12.6 Grafana Dashboard Panels

The pre-configured dashboard (`network-overview.json`) includes:
- Device reachability status grid (UP/DOWN per device)
- CPU/Memory utilization time series with thresholds
- Devices up by campus (bar gauge)
- Protocol health: OSPF neighbors, BGP sessions, BFD status
- HSRP active groups across all campuses

---

## 14. Security Design

### 14.1 VTY Access Control

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

### 13.2 Credential Management

| Account | Purpose | Privilege |
|---------|---------|-----------|
| admin | Primary admin account | 15 |

**Environment-based Credentials**: Device credentials are stored in `.env` and loaded via environment variables. The `.env` file is excluded from version control (`.gitignore`) to prevent credential exposure.

```bash
# Create .env file from template
cp .env.example .env

# Edit with your credentials
vim .env
```

The pyATS testbed files use `%ENV{VAR_NAME}` syntax to reference credentials from the environment.

### 13.3 Secure Credential Wrappers

For production-grade security, wrapper scripts load credentials from **macOS Keychain** instead of environment files:

```bash
# Store credentials in Keychain (one-time setup)
security add-generic-password -a "$USER" -s "euniv-username" -w "your-username"
security add-generic-password -a "$USER" -s "euniv-password" -w "your-password"
security add-generic-password -a "$USER" -s "euniv-enable" -w "your-enable-password"

# Run pyATS tests with secure credentials
cd pyats
./run.sh hsrp_job.py --testbed-file testbed.yaml

# Run deployment scripts with secure credentials
cd scripts
./run.sh configure_hsrp.py --testbed ../pyats/testbed.yaml
```

The wrapper scripts (`pyats/run.sh`, `scripts/run.sh`) automatically:
1. Retrieve credentials from macOS Keychain
2. Export them as environment variables
3. Execute the specified script

### 13.4 SSH Configuration

- SSH Version 2 only
- RSA key: 2048 bits
- VTY timeout: 30 minutes

---

## 15. Automation Framework

### 15.1 Source of Truth

**NetBox** (Cloud-hosted)
- URL: https://'<your-netbox-website-address>'
- Contains: Device inventory, IPs, connections, custom fields

### 14.2 Configuration Pipeline

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  NetBox  │ ──▶ │  Jinja2  │ ──▶ │  pyATS   │ ──▶ │  Device  │
│  (SoT)   │     │ Templates│     │  Deploy  │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

### 14.3 Automation Scripts

#### Core Scripts

| Script | Purpose |
|--------|---------|
| `generate_configs.py` | Generate configs from templates |
| `validate.py` | Pre/post deployment validation |
| `deploy.py` | Deploy configs with backup/rollback |
| `orchestrate.py` | Full pipeline orchestration (generate → validate → deploy) |

#### Deployment Scripts

| Script | Purpose |
|--------|---------|
| `configure_bfd.py` | Deploy BFD on edge links (100ms interval, 3x multiplier = 300ms detection) |
| `configure_ha.py` | Deploy HSRP HA on PE router pairs (1s hello, 3s hold, HSRPv2) |
| `deploy_inet.py` | Deploy Internet gateway BGP configuration |
| `deploy_customer_traffic.py` | Deploy L3VPN/customer traffic on Edge routers |
| `deploy_host_interfaces.py` | Configure Edge router Gi6 interfaces in STAFF-NET VRF |
| `deploy_host_switches.py` | Configure IOSv host routers with IP SLA traffic generation |
| `fix_edge.py` | Apply Edge router fixes and corrections |
| `fix_vpnv4_rr.py` | Configure VPNv4 route-reflector-client on AGG routers |

#### Verification Scripts

| Script | Purpose |
|--------|---------|
| `verify_l3vpn.py` | Verify VPNv4 BGP and cross-campus VRF connectivity |
| `verify_bfd.py` | Verify BFD neighbors and test failover detection |
| `verify_internet.py` | Verify Internet gateway connectivity |
| `troubleshoot.py` | Comprehensive troubleshooting across all protocols |
| `export_video_baseline.py` | Export baseline configurations for documentation |

#### Traffic Test Scripts

| Script | Framework | Purpose |
|--------|-----------|---------|
| `traffic_test.py` | Netmiko | Fast end-to-end traffic test (~3s quick, ~60s full) |
| `traffic_test_pyats.py` | pyATS/Genie | pyATS-based traffic test with structured parsing |
| `pyats/tests/validate_network.py` | pyATS | Comprehensive network validation (OSPF, BGP, MPLS, VRF, traffic, internet) |
| `pyats/tests/test_euniv_network.py` | pyATS | Network validation tests with JSON output support |
| `scripts/shutdown_unused_interfaces.py` | pyATS | Admin shutdown unused Gi4 interfaces on EDGE devices |

**Traffic Test Usage:**
```bash
# Quick connectivity check (Netmiko - faster)
python traffic_test.py --quick

# Full throughput + traceroute test
python traffic_test.py

# pyATS version with testbed
python traffic_test_pyats.py --quick
python traffic_test_pyats.py --testbed pyats/host_testbed.yaml
```

**JSON Output Structure (traffic tests):**
- `test_metadata`: Timestamp, duration, hosts tested
- `connectivity_matrix`: Host-to-host reachability with latency
- `throughput_results`: Measured throughput per path (Mbps)
- `traceroute_results`: Path hops with MPLS label detection
- `summary`: Aggregate statistics (min/max/avg latency and throughput)

**Network Validation Tests:**
```bash
# Run all validation tests
python pyats/tests/test_euniv_network.py --testbed pyats/testbed.yaml

# Run specific test category
python pyats/tests/test_euniv_network.py --testbed pyats/testbed.yaml --test bgp

# Export results to JSON
python pyats/tests/test_euniv_network.py --testbed pyats/testbed.yaml --json-output results.json

# Test single device with JSON output
python pyats/tests/test_euniv_network.py --testbed pyats/testbed.yaml --device EUNIV-CORE1 -j core1.json
```

**pyATS Job-based Validation (Recommended):**
```bash
# Run full network validation via pyATS job
cd pyats
pyats run job euniv_job.py --testbed-file testbed.yaml

# Generate HTML report
pyats run job euniv_job.py --testbed-file testbed.yaml --html-logs ./reports

# View logs from last run
pyats logs view
```

> **Note**: The pyATS job automatically loads credentials from the `.env` file in the project root. Ensure your `.env` file contains `DEVICE_USERNAME`, `DEVICE_PASSWORD`, and `DEVICE_ENABLE_PASSWORD`.

#### Orchestration Pipeline

```bash
# Full automated deployment
python orchestrate.py --execute

# Plan mode (dry-run)
python orchestrate.py --plan

# Generate configs only
python orchestrate.py --generate-only

# Validate only (no deployment)
python orchestrate.py --validate-only
```

### 14.4 Validation Tests

| Test | Description |
|------|-------------|
| Connectivity | SSH reachability to all devices |
| Interfaces | Configured interfaces up/up |
| OSPF | All expected neighbors in FULL state |
| BGP | All sessions Established |
| MPLS LDP | All LDP neighbors Operational |
| L3VPN/VPNv4 | VRF routes exchanged across campuses |
| BFD | All BFD neighbors up with correct timers |
| Internet | Gateway reachability and BGP to upstream |

### 14.5 NetBox Integration

Populate NetBox with device inventory using:

```bash
# Full population (devices, IPs, interfaces, connections)
python netbox/populate_euniv.py

# Cleanup existing data first
python netbox/populate_euniv.py --cleanup

# Verify population
python netbox/populate_euniv.py --verify
```

### 14.6 EVE-NG Lab Integration

The project includes complete EVE-NG lab configurations:

| Directory | Contents |
|-----------|----------|
| `E-University-Baseline/configs/` | 22 complete baseline configs (16 network + 6 HOST devices) |
| `eve-ng/TOPOLOGY_GUIDE.md` | Full cabling guide with interface mappings |
| `eve-ng/startup-configs/` | 16 minimal startup configs for initial boot |
| `eve-ng/full-configs/` | 16 complete configs with all protocols |

**Baseline Configs Include:**
- 16 Network devices: CORE1-5, INET-GW1-2, AGG1 (x3), PE1-2 (x3 campuses)
- 6 HOST devices: HOST1-6 (IOSv routers for traffic generation)
- All devices configured with static management IPs (192.168.68.x)
- Complete OSPF, BGP, MPLS, VRF configurations

```bash
# Generate startup configs
python eve-ng/generate_startup_configs.py

# Generate full configs
python eve-ng/generate_full_configs.py
```

---

## 16. Appendix

### 16.1 Verification Commands

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

# BFD
show bfd neighbors
show bfd neighbors detail
```

### 15.2 Troubleshooting Checklist

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

4. **BFD Neighbors Down**
   - Verify `bfd interval` configured on both ends
   - Check `bfd all-interfaces` under `router ospf 1`
   - Confirm OSPF neighbor is FULL (BFD requires OSPF)
   - Check for hardware/platform BFD support

### 15.3 Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-27 | Network Team | Initial release |
| 1.1 | 2025-12-02 | Network Team | Added BFD, deployment/verification scripts, EVE-NG integration, NetBox population docs |
| 1.2 | 2025-12-02 | Network Team | Renamed PE routers to Edge routers, added Host layer with 6 Linux hosts for traffic generation |
| 1.3 | 2025-12-02 | Network Team | Replaced Linux hosts with IOSv routers for traffic generation via IP SLA probes, fixed VPNv4 route reflection on AGG routers, added host deployment scripts |
| 1.4 | 2025-12-02 | Network Team | Added end-to-end traffic test scripts (Netmiko + pyATS versions) with JSON output for visualization, created pyATS host testbed |
| 1.5 | 2025-12-02 | Network Team | Added comprehensive network validation test (validate_network.py), interface shutdown automation script |
| 1.6 | 2025-12-02 | Network Team | Added JSON output support to test_euniv_network.py for exporting test results |
| 1.7 | 2025-12-02 | Network Team | Configured static management IPs on all devices (previously DHCP), updated baseline configs |
| 1.8 | 2025-12-02 | Network Team | Added HOST1-6 configs to baseline folder for complete lab deployment |
| 1.9 | 2025-12-02 | Network Team | Added credential protection - credentials now use environment variables via .env file, removed from git history |
| 2.0 | 2025-12-03 | Network Team | Deployed BFD on edge links (Core↔INET-GW, AGG↔Edge) with 300ms detection time, added BFD design section, updated pyATS validation tests |
| 2.1 | 2025-12-03 | Network Team | Deployed HSRP HA on PE router pairs (HSRPv2, 1s hello, 3s hold), added Section 7.4 HSRP design, created configure_ha.py script |
| 2.2 | 2025-12-03 | Network Team | Added shutdown_unused_interfaces.py script to admin shutdown Gi4 on EDGE devices (unused interfaces causing false alerts). Fixed CPU metric collection in network-monitor for CSR1000V (uses SNMP index .7 instead of .1). Added interactive D3.js topology map to network-monitor frontend. |
| 2.3 | 2025-12-05 | Network Team | Fixed pyATS credential loading - added load_dotenv() to euniv_job.py for automatic .env file loading. Added device health monitoring job and tests. Code style cleanup across all scripts. |
| 3.0 | 2025-12-05 | Network Team | Added streaming telemetry stack (Grafana + InfluxDB + Python collector) for real-time network observability. Implemented HSRP gateway redundancy across all 3 campuses with load balancing (11 groups). Added pyATS HSRP validation tests. Created secure credential wrappers using macOS Keychain. Added chaos testing and IPv6 deployment scripts. |
| 3.1 | 2025-12-07 | Network Team | Implemented centralized VRF internet access via INET-GW with VRF-aware NAT. Added Access Layer SVI design with HSRP on Gi4 subinterfaces. Deployed centralized DHCP services via dnsmasq container. Added QoS section with VRF-based traffic classification and hierarchical queuing. Created inet_gw_aetest.py for NAT/VRF connectivity validation. |

---

**End of Document**
