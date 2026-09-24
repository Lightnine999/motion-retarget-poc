import unreal
import json
import math

REPORT = {}


def quat_angle_deg(q1, q2):
    dot = abs(q1.x * q2.x + q1.y * q2.y + q1.z * q2.z + q1.w * q2.w)
    dot = min(1.0, max(-1.0, dot))
    return math.degrees(2 * math.acos(dot))


anim_path = "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo"
anim = unreal.EditorAssetLibrary.load_asset(anim_path)
track_names = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(anim)]
num_frames = unreal.AnimationLibrary.get_num_frames(anim)
REPORT["num_frames"] = num_frames
REPORT["num_tracks"] = len(track_names)

per_track = {}
for track in track_names[:5]:
    rot = list(unreal.AnimationLibrary.get_raw_track_rotation_data(anim, track))
    max_delta = None
    if len(rot) > 1:
        deltas = [quat_angle_deg(rot[i], rot[i + 1]) for i in range(len(rot) - 1)]
        max_delta = max(deltas)
    per_track[track] = {"rot_len": len(rot), "max_delta": max_delta}

REPORT["per_track_sample"] = per_track

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/21_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
