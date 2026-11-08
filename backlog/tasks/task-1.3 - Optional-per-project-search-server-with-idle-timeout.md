---
id: TASK-1.3
title: Optional per-project search server with idle timeout
status: Idea
assignee: []
created_date: '2026-11-08T11:03:00Z'
labels: []
dependencies: []
parent_task_id: TASK-1
type: feature
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Idea from the user: searches come in bursts, so the first search could start a temporary per-project backend that keeps the index and vector store open and exits after a configurable idle time (about 15 s to 1 min). Measured warm search today is about 0.15 s, of which about 0.07 s is Python startup that a CLI client still pays; a server would save roughly 50-100 ms per query. Open points: lifecycle and races on start, stale index after refresh, Windows IPC (named pipes), interplay with the exclusive index lock. Decide after measuring the MVP on large repositories. Needs analysis before implementation.
<!-- SECTION:DESCRIPTION:END -->
