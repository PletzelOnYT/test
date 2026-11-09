#!/usr/bin/env python3
"""Verbatim regression fixtures from the exact compiled HTML run #42541737782."""
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from evidence_metrics import extract,stall_failures

HERE=Path(__file__).parent
FIXTURES=HERE/"fixtures"

class EvidenceParserRegression(unittest.TestCase):
    def test_survival_13438ms(self):
        m=extract(json.loads((FIXTURES/"survival-stall.json").read_text()))
        self.assertEqual(m["max_any_sync_chunk_wait_ms"],13438)
        self.assertEqual(m["max_since_completed_heartbeat_ms"],34019)
        self.assertTrue(stall_failures(m,"survival"))

    def test_onecpu_22505ms(self):
        m=extract(json.loads((FIXTURES/"onecpu-stall.json").read_text()))
        self.assertEqual(m["max_any_sync_chunk_wait_ms"],22505)
        self.assertEqual(m["max_since_completed_heartbeat_ms"],67215)
        self.assertTrue(stall_failures(m,"onecpu"))

    def test_missing_required_heartbeat_fails(self):
        self.assertTrue(stall_failures(extract([]),"survival"))

    def test_malformed_native_marker_fails(self):
        m=extract([{"t":1,"text":"[EagPerfHeartbeat] lastTick=1 sinceCompleted=1ms"},
                   {"t":2,"text":"[EagPerfChunkWait] elapsed=unknownms"}])
        self.assertEqual(m["malformed_chunk_wait_events"],1)
        self.assertTrue(stall_failures(m,"survival"))

    def test_healthy_trace_can_pass_core_parser(self):
        events=[{"t":i,"text":f"[EagPerfHeartbeat] lastTick={20*i} sinceCompleted=10ms"} for i in range(15)]
        self.assertFalse(stall_failures(extract(events),"survival"))

    def test_strict_gate_process_rejects_exact_wait_fixtures(self):
        for kind,wait,age in (("survival",13438,34019),("onecpu",22505,67215)):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
                root=Path(d);(root/"singleplayer-pressure-evidence").mkdir()
                events=json.loads((FIXTURES/(kind+"-stall.json")).read_text())
                (root/"singleplayer-pressure-evidence/events.json").write_text(json.dumps(events))
                env=os.environ.copy();env["TEST_KIND"]=kind;env["VARIANT"]="fixture"
                a=subprocess.run([sys.executable,str(HERE/"analyze-candidate-gameplay.py")],
                                 cwd=root,env=env,text=True,capture_output=True)
                self.assertEqual(a.returncode,0,a.stdout+a.stderr)
                g=subprocess.run([sys.executable,str(HERE/"strict-evidence-gate.py")],
                                 cwd=root,env=env,text=True,capture_output=True)
                self.assertEqual(g.returncode,2,g.stdout+g.stderr)
                report=json.loads((root/"strict-evidence-gate.json").read_text())
                self.assertEqual(report["max_any_sync_chunk_wait_ms"],wait)
                self.assertEqual(report["max_since_completed_heartbeat_ms"],age)
                self.assertFalse(report["automatic_gate_pass"])
                self.assertTrue(any("max_any_sync_chunk_wait_ms" in x for x in report["failures"]))

if __name__=="__main__":unittest.main()
