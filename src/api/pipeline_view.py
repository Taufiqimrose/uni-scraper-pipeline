"""Build a structured pipeline view from a ScrapeJob for the /pipeline endpoint."""

from datetime import datetime

from src.models import PipelineStatusResponse, PipelineStep, ScrapeJob, ScrapeStatus

# Ordered pipeline phases — maps internal step keywords to display names
PIPELINE_PHASES: list[tuple[str, list[str]]] = [
    ("Initializing", ["initializing", "Initializing"]),
    ("Planning", ["planning", "Analyzing site structure"]),
    ("Discovering Programs", ["discovering", "Discovering programs", "discovering_programs"]),
    ("Extracting Programs", ["extracting", "Extracting program", "extracting_programs"]),
    ("Validating", ["validating", "Validating extracted data"]),
    ("Storing", ["storing", "Storing data"]),
    ("Complete", ["complete", "Complete"]),
]

# Terminal statuses
_TERMINAL = {ScrapeStatus.COMPLETED, ScrapeStatus.FAILED, ScrapeStatus.PARTIAL}


def _match_phase(step_text: str) -> str | None:
    """Match a step/phase string to one of the known pipeline phase names."""
    lower = step_text.lower()
    for phase_name, keywords in PIPELINE_PHASES:
        for kw in keywords:
            if kw.lower() in lower:
                return phase_name
    return None


def build_pipeline_view(job: ScrapeJob) -> PipelineStatusResponse:
    """Transform a ScrapeJob (with its agent_log) into a structured pipeline response."""

    # Walk the agent_log to find timing per phase
    phase_events: dict[str, list[dict]] = {}  # type: ignore[type-arg]
    for entry in job.agent_log:
        phase_text = entry.get("phase", "")
        matched = _match_phase(phase_text)
        if matched:
            phase_events.setdefault(matched, []).append(entry)

    # Determine which phase is currently active
    current_phase = _match_phase(job.current_step or "") if job.current_step else None

    # Build steps
    steps: list[PipelineStep] = []
    seen_current = False

    for phase_name, _keywords in PIPELINE_PHASES:
        if phase_name == "Complete":
            continue  # "Complete" is not shown as a step

        events = phase_events.get(phase_name, [])

        # Determine step status
        if events:
            timestamps = [e.get("timestamp") for e in events if e.get("timestamp")]
            first_ts = min(timestamps) if timestamps else None
            last_ts = max(timestamps) if timestamps else None

            # Check if any event in this phase was a failure
            has_failure = any(e.get("status") == "failed" for e in events)

            if has_failure:
                step_status = "failed"
            elif phase_name == current_phase and job.status not in _TERMINAL:
                step_status = "running"
                seen_current = True
            else:
                step_status = "completed"

            # Compute duration
            duration = None
            if first_ts and last_ts and first_ts != last_ts:
                try:
                    t0 = datetime.fromisoformat(first_ts)
                    t1 = datetime.fromisoformat(last_ts)
                    duration = (t1 - t0).total_seconds()
                except (ValueError, TypeError):
                    pass

            # Build detail from latest event
            latest = events[-1]
            detail = _build_detail(phase_name, latest)

            steps.append(PipelineStep(
                name=phase_name,
                status=step_status,
                started_at=first_ts,
                completed_at=last_ts if step_status in ("completed", "failed") else None,
                duration_seconds=duration,
                detail=detail,
            ))
        else:
            # No events yet for this phase
            if seen_current or (current_phase and phase_name != current_phase and not phase_events.get(phase_name)):
                step_status = "pending"
            elif phase_name == current_phase:
                step_status = "running"
                seen_current = True
            else:
                step_status = "pending"

            steps.append(PipelineStep(
                name=phase_name,
                status=step_status,
            ))

    # Handle failed status: mark remaining pending steps
    if job.status == ScrapeStatus.FAILED:
        failed_seen = False
        for step in steps:
            if step.status == "failed":
                failed_seen = True
            elif failed_seen and step.status in ("running", "pending"):
                step.status = "skipped"

    # Compute elapsed time
    elapsed = None
    if job.started_at:
        end = job.completed_at or datetime.utcnow()
        elapsed = (end - job.started_at).total_seconds()

    return PipelineStatusResponse(
        job_id=job.id,
        university_name=job.university_name,
        major_name=job.major_name,
        overall_status=job.status,
        progress=job.progress,
        steps=steps,
        metrics={
            "tokens_used": job.total_tokens_used,
            "pages_fetched": job.total_pages_fetched,
            "programs_found": job.programs_found,
            "programs_scraped": job.programs_scraped,
            "courses_found": job.courses_found,
        },
        started_at=job.started_at.isoformat() if job.started_at else None,
        elapsed_seconds=round(elapsed, 1) if elapsed is not None else None,
    )


def _build_detail(phase_name: str, event: dict) -> str | None:  # type: ignore[type-arg]
    """Build a human-readable detail string from a log event."""
    msg = event.get("message", "")

    if phase_name == "Discovering Programs":
        found = event.get("programs_found", 0)
        if found:
            return f"Found {found} programs"
    elif phase_name == "Extracting Programs":
        scraped = event.get("programs_scraped", 0)
        found = event.get("programs_found", 0)
        if found:
            return f"Extracted {scraped}/{found} programs"
    elif phase_name == "Validating":
        return msg if msg and msg != "Entered: Validating extracted data" else "Checking data quality"
    elif phase_name == "Storing":
        courses = event.get("courses_found", 0)
        if courses:
            return f"Saved {courses} courses to database"

    # Fallback: use message if it's not a generic "Entered:" message
    if msg and not msg.startswith("Entered:"):
        return msg

    return None
