import argparse
import asyncio

from src.main import (
    EDGE_DEVICE_UID,
    MAX_BATCH_SIZE,
    generate_demo_event,
    list_queue,
    queue_event,
    queue_summary,
    send_heartbeat,
    sync_pending_events,
)


async def cmd_generate(args: argparse.Namespace) -> None:
    for _ in range(args.count):
        event = generate_demo_event(event_type=args.event_type, confidence=args.confidence)
        queue_event(event)
    print(f"Generated {args.count} event(s) for device {EDGE_DEVICE_UID}")
    print(queue_summary())


async def cmd_queue(args: argparse.Namespace) -> None:
    events = list_queue()
    print(f"Queue entries: {len(events)}")
    print("event_id | event_type | confidence | status | sync_attempts | last_error")
    for event in events:
        print(f"{event.event_id} | {event.event_type} | {event.confidence} | {event.status} | {event.sync_attempts} | {event.last_error}")
    print(queue_summary())


async def cmd_sync(args: argparse.Namespace) -> None:
    result = await sync_pending_events(offline=args.offline, fail_sync=args.fail_sync)
    print(result)


async def cmd_heartbeat(args: argparse.Namespace) -> None:
    print(await send_heartbeat())


async def cmd_status(args: argparse.Namespace) -> None:
    print({"device_uid": EDGE_DEVICE_UID, "max_batch_size": MAX_BATCH_SIZE, "queue_summary": queue_summary()})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Demo edge simulator for offline store-and-forward ingestion")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate offline events and enqueue them")
    generate.add_argument("--count", type=int, default=1)
    generate.add_argument("--event-type", default="Cough")
    generate.add_argument("--confidence", type=float, default=0.91)
    generate.set_defaults(func=cmd_generate)

    queue = subparsers.add_parser("queue", help="Inspect the local queue")
    queue.set_defaults(func=cmd_queue)

    sync = subparsers.add_parser("sync", help="Synchronize queued events")
    sync.add_argument("--offline", action="store_true")
    sync.add_argument("--fail-sync", action="store_true")
    sync.set_defaults(func=cmd_sync)

    heartbeat = subparsers.add_parser("heartbeat", help="Send a demo heartbeat")
    heartbeat.set_defaults(func=cmd_heartbeat)

    status = subparsers.add_parser("status", help="Print queue and device status")
    status.set_defaults(func=cmd_status)

    return parser


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    await args.func(args)


if __name__ == "__main__":
    asyncio.run(main())
