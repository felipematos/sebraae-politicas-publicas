#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline Progress Monitor
Continuously monitors and logs queue processing progress
"""

import asyncio
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ProgressMonitor:
    def __init__(self):
        self.db_path = "falhas_mercado_v1.db"
        self.log_file = Path("progress_log.jsonl")
        self.metrics_file = Path("progress_metrics.json")

    def get_queue_status(self) -> dict:
        """Get current queue status from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'concluído' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'processando' THEN 1 ELSE 0 END) as processing,
                SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'erro' THEN 1 ELSE 0 END) as error
            FROM fila_pesquisas
        """)
        queue = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) FROM resultados_pesquisa")
        results_count = cursor.fetchone()[0]

        # Language distribution
        cursor.execute("""
            SELECT idioma, COUNT(*) as total
            FROM resultados_pesquisa
            GROUP BY idioma
            ORDER BY total DESC
        """)
        lang_dist = {row[0]: row[1] for row in cursor.fetchall()}

        # Translation coverage
        cursor.execute("""
            SELECT
                SUM(CASE WHEN titulo_pt IS NOT NULL THEN 1 ELSE 0 END) as with_pt,
                SUM(CASE WHEN titulo_en IS NOT NULL THEN 1 ELSE 0 END) as with_en
            FROM resultados_pesquisa
        """)
        translations = cursor.fetchone()

        conn.close()

        return {
            "timestamp": datetime.now().isoformat(),
            "queue": {
                "total": queue[0] or 0,
                "completed": queue[1] or 0,
                "processing": queue[2] or 0,
                "pending": queue[3] or 0,
                "error": queue[4] or 0,
                "completion_pct": (queue[1] / queue[0] * 100) if queue[0] else 0,
            },
            "results": {
                "total": results_count,
                "with_pt": translations[0] or 0,
                "with_en": translations[1] or 0,
                "language_distribution": lang_dist,
            },
        }

    def log_progress(self, status: dict):
        """Log progress to JSONL file"""
        with open(self.log_file, "a") as f:
            f.write(json.dumps(status) + "\n")

    def save_metrics(self, status: dict):
        """Save current metrics to JSON"""
        with open(self.metrics_file, "w") as f:
            json.dump(status, f, indent=2)

    def print_status(self, status: dict):
        """Print formatted status"""
        q = status["queue"]
        r = status["results"]

        print("\n" + "=" * 80)
        print(f"PIPELINE PROGRESS - {datetime.fromisoformat(status['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()
        print("QUEUE STATUS:")
        print(f"  Total entries:    {q['total']}")
        print(f"  ✅ Completed:     {q['completed']}")
        print(f"  🔄 Processing:    {q['processing']}")
        print(f"  ⏳ Pending:       {q['pending']}")
        print(f"  ❌ Errors:        {q['error']}")
        print(f"  📈 Completion:    {q['completion_pct']:.2f}%")
        print()
        print("RESULTS:")
        print(f"  Total results:    {r['total']}")
        print(f"  With PT trans:    {r['with_pt']}")
        print(f"  With EN trans:    {r['with_en']}")
        print()
        print("LANGUAGE DISTRIBUTION:")
        for lang, count in sorted(r['language_distribution'].items(), key=lambda x: -x[1]):
            print(f"  {lang:<5} {count:>6}")

    async def monitor(self, interval: int = 30):
        """Continuously monitor progress"""
        print("Starting progress monitor...")
        iteration = 0
        last_completed = 0

        try:
            while True:
                status = self.get_queue_status()
                self.log_progress(status)
                self.save_metrics(status)

                # Calculate rate
                current_completed = status["queue"]["completed"]
                rate = (current_completed - last_completed) / (interval / 3600)  # entries per hour
                last_completed = current_completed

                # Print with rate info
                self.print_status(status)
                print(f"Processing rate: ~{rate:.1f} entries/hour")
                print(f"(Monitor iteration: {iteration})")

                iteration += 1
                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            print("\n\nMonitor stopped by user")
            sys.exit(0)


async def main():
    monitor = ProgressMonitor()
    await monitor.monitor(interval=30)


if __name__ == "__main__":
    asyncio.run(main())
