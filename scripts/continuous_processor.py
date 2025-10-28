#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Continuous Queue Processor
Processes pending research entries from the queue continuously
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agente.processador import Processador
from app.config import settings


async def main():
    """Main processor loop"""
    print("=" * 80)
    print("CONTINUOUS RESEARCH QUEUE PROCESSOR")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Configuration: {settings.dict()}")
    print()

    processador = Processador()

    try:
        await processador.processar_tudo(intervalo_verificacao=5)
    except KeyboardInterrupt:
        print("\n\nProcessor interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nProcessor error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
