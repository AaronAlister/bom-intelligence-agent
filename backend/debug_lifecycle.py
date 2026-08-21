import asyncio

from backend.app.intelligence.enrichment.arrow import ArrowProvider
from backend.app.intelligence.enrichment.digikey import DigiKeyProvider
from backend.app.intelligence.enrichment.mouser import MouserProvider


async def main() -> None:
    providers = [
        MouserProvider(),
        ArrowProvider(),
        DigiKeyProvider(),
    ]

    for provider in providers:
        print(f"\n=== {provider.name} ===")

        try:
            result = await provider.enrich(
                mpn="STM32F407VGT6",
                manufacturer="STMicroelectronics",
            )

            if result is None:
                print("RESULT: None")
                continue

            print("MPN:", result.mpn)
            print("Manufacturer:", result.manufacturer)
            print("Lifecycle:", result.lifecycle_status)
            print("Availability:", result.availability)
            print("Source:", result.source)

        except Exception as exc:
            print("ERROR:", type(exc).__name__, str(exc))


if __name__ == "__main__":
    asyncio.run(main())
