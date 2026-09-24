import unreal
import json

REPORT = {}
names = [n for n in dir(unreal) if "Export" in n and ("Fbx" in n or "FBX" in n)]
REPORT["export_classes"] = names

REPORT["skel_export_dir"] = [a for a in dir(unreal.SkeletalMeshExporterFBX) if not a.startswith("_")]
REPORT["asset_export_task_dir"] = [a for a in dir(unreal.AssetExportTask) if not a.startswith("_")]
REPORT["help_export_task"] = unreal.Exporter.run_asset_export_task.__doc__ if hasattr(unreal.Exporter, "run_asset_export_task") else "no run_asset_export_task"
REPORT["exporter_dir"] = [a for a in dir(unreal.Exporter) if not a.startswith("_")]

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/51_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
