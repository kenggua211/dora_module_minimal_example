# Dora-rs Module Composition – Minimal Example

This repository provides a minimal example for the **Dora-rs module composition proposal**.

It demonstrates how an external tool can expand and compose reusable dataflows, allowing users to integrate existing dataflow modules into their own projects.

## Usage

### 1. Generate the composed dataflow

```bash
uv run compose.py dataflow.yml
```

This command generates a new file:

```
composed.yml
```

### 2. Run the composed dataflow

```bash
dora run composed.yml
```

This starts the composed Dora dataflow.

## Core Idea

The goal of this example is to demonstrate a simple way to reuse and compose Dora dataflows.

An external expansion tool (`compose.py`) merges a **sub-dataflow** into a user's main dataflow definition. This makes it easy to integrate reusable components created by others into a larger system.

By enabling modular composition of dataflows, the community can more easily:

* reuse existing components
* share dataflow modules
* build more complex systems collaboratively

## Motivation

As Dora projects grow, dataflows can become large and difficult to maintain.
A modular composition approach allows developers to break complex systems into smaller reusable dataflows and combine them when needed.

This example illustrates one possible approach to implementing such a workflow.
