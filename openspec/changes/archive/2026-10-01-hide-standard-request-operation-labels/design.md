# Design

## Context

The shared table uses requestTypeLabel for its secondary line; request details use requestOperationLabel independently.

## Goals / Non-Goals

Remove routine label noise without hiding special operations or workload information.
No changes to classification, storage, API schemas, routing, billing or details.

## Decisions

Suppress exactly Responses and Messages in the table formatter, not by provider/model name. Compose the remaining operation and workload with no duplicate or dangling separator. Render the line only for a nonempty result.

## Risks / Trade-offs

Accidentally hiding special events → test every supported operation and public table rendering.
Empty margin or lost details → assert absent secondary DOM for ordinary rows and explicit operation in details.
