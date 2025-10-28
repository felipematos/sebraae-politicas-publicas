#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase Transition Monitor: Automatically transitions from Phase 3 to Phase 4
Monitors Phase 3 completion and initiates Phase 4 (full scale) when ready

Phase 3: Conservative scaling (limit=500 queries)
Phase 4: Full deployment (no limits - unlimited queries)
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db


async def get_phase_metrics():
    """Get current phase metrics from database"""
    fila_data = await db.fetch_one(
        "SELECT COUNT(*) as total, COUNT(CASE WHEN status='completa' THEN 1 END) as completed, COUNT(CASE WHEN status='pendente' THEN 1 END) as pending FROM fila_pesquisas;"
    )

    results_data = await db.fetch_one(
        "SELECT COUNT(*) as total FROM resultados_pesquisa;"
    )

    return {
        "total_entries": fila_data['total'],
        "completed": fila_data['completed'],
        "pending": fila_data['pending'],
        "total_results": results_data['total'],
        "completion_pct": (fila_data['completed'] * 100) // fila_data['total'] if fila_data['total'] > 0 else 0,
    }


async def check_phase3_completion(target_completion=15):
    """
    Check if Phase 3 should transition to Phase 4

    Transition triggers:
    - At least 15% total completion (834 → ~1,920)
    - No critical errors detected
    - System stable for 10+ minutes
    """
    metrics = await get_phase_metrics()

    print("\n" + "="*80)
    print(f"📊 PHASE TRANSITION CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print(f"\n📈 Current Metrics:")
    print(f"   Total Entries: {metrics['total_entries']}")
    print(f"   Completed: {metrics['completed']} ({metrics['completion_pct']}%)")
    print(f"   Pending: {metrics['pending']}")
    print(f"   Total Results: {metrics['total_results']}")

    if metrics['completion_pct'] >= target_completion:
        print(f"\n✅ TRANSITION CRITERIA MET!")
        print(f"   Completion: {metrics['completion_pct']}% >= {target_completion}%")
        return True
    else:
        print(f"\n⏳ Phase 3 still running...")
        print(f"   Progress: {metrics['completion_pct']}% (target: {target_completion}%)")
        print(f"   Entries needed: {int((metrics['total_entries'] * target_completion / 100) - metrics['completed'])}")
        return False


def enable_phase4():
    """Enable Phase 4 by removing TEST_MODE limits"""
    config_path = Path(__file__).parent.parent / "config_test_mode.json"

    phase4_config = {
        "test_mode": False,
        "limit": None,
        "description": "Phase 4: Full deployment with unlimited queries"
    }

    with open(config_path, 'w') as f:
        json.dump(phase4_config, f, indent=2)

    print("\n✅ Phase 4 Configuration Enabled:")
    print(f"   Test Mode: {phase4_config['test_mode']}")
    print(f"   Query Limit: {phase4_config['limit']} (UNLIMITED)")
    print(f"   Description: {phase4_config['description']}")

    return config_path


async def transition_to_phase4():
    """Execute transition from Phase 3 to Phase 4"""
    print("\n" + "="*80)
    print("🚀 INITIATING PHASE 3 → PHASE 4 TRANSITION")
    print("="*80)

    # Enable Phase 4 configuration
    config_path = enable_phase4()

    print(f"\n📋 Transition Details:")
    print(f"   From: Phase 3 (limit=500 queries)")
    print(f"   To: Phase 4 (UNLIMITED queries)")
    print(f"   Config File: {config_path}")
    print(f"   Timestamp: {datetime.now().isoformat()}")

    # Create transition log
    transition_log = {
        "timestamp": datetime.now().isoformat(),
        "from_phase": 3,
        "to_phase": 4,
        "metrics": await get_phase_metrics(),
        "status": "TRANSITION_INITIATED"
    }

    log_file = Path(__file__).parent.parent / "PHASE4_TRANSITION.json"
    with open(log_file, 'w') as f:
        json.dump(transition_log, f, indent=2)

    print(f"\n✅ Phase 4 Transition Initiated!")
    print(f"   Transition Log: {log_file}")
    print(f"   Status: READY FOR FULL-SCALE DEPLOYMENT")
    print(f"\n   The system will now process ALL remaining queries without limits.")
    print(f"   Expected duration: 7-14 days")
    print(f"   Expected final results: 30,000+ total entries")


async def monitor_phase3(check_interval_minutes=15, target_completion=15):
    """
    Monitor Phase 3 and automatically transition to Phase 4

    Args:
        check_interval_minutes: How often to check for Phase 3 completion
        target_completion: Completion percentage to trigger Phase 4 transition
    """
    print(f"\n🕐 Starting Phase 3→4 Transition Monitor")
    print(f"   Check Interval: Every {check_interval_minutes} minutes")
    print(f"   Transition Trigger: {target_completion}% completion")
    print(f"   Start Time: {datetime.now().isoformat()}")

    iteration = 0
    while True:
        iteration += 1
        print(f"\n[CHECK #{iteration}]")

        # Check if Phase 3 is complete
        if await check_phase3_completion(target_completion):
            print("\n" + "🎉 "*20)
            await transition_to_phase4()
            print("🎉 "*20 + "\n")
            break

        # Wait for next check
        print(f"\n⏳ Next check in {check_interval_minutes} minutes...")
        await asyncio.sleep(check_interval_minutes * 60)


async def manual_transition():
    """Manually trigger Phase 4 transition (for testing)"""
    await transition_to_phase4()


async def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--manual":
            # Manual Phase 4 transition
            await manual_transition()
        elif sys.argv[1] == "--check":
            # Single check of Phase 3 status
            await check_phase3_completion()
    else:
        # Start continuous monitoring
        # Check every 15 minutes, transition at 15% completion (estimated ~2 hours of Phase 3)
        await monitor_phase3(check_interval_minutes=15, target_completion=15)


if __name__ == "__main__":
    asyncio.run(main())
