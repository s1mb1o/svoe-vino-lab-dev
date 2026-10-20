"""Choose mask geometry without candidate scores or query truth."""
import numpy as np
from PIL import Image
import bottle_orientation


def best_angle(image):
    alpha = image.getchannel("A")
    core = np.asarray(alpha) >= 128
    hull = bottle_orientation._hull(core)
    if len(hull) < 3 or core.sum() < 16:
        return 0., {"reason": "empty_or_tiny_mask"}
    angle, aspect = bottle_orientation._angle(hull)
    probe = Image.fromarray(core.astype(np.uint8) * 255)
    probe.thumbnail((512, 512), Image.Resampling.NEAREST)
    probe = probe.rotate(angle, Image.Resampling.NEAREST, expand=True, fillcolor=0)
    neck, ratio = bottle_orientation._neck(probe)
    if neck == "bottom":
        angle = (angle + 360) % 360 - 180
    return float(angle), {"axis_aspect": aspect, "neck": neck, "neck_ratio": ratio,
                          "mask_area": int(core.sum()), "geometry_step_degrees": .05}


def policy_angle(angle, policy):
    if policy == "iou-min5" and abs(angle) < 5:
        return 0.
    if policy == "iou-cardinal5" and abs((angle + 45) % 90 - 45) < 5:
        return 0.
    return angle


def transform(image, angle):
    result = image
    if angle:
        result = image.rotate(angle, Image.Resampling.BICUBIC, expand=True,
                              fillcolor=(255, 255, 255, 0))
    box = result.getchannel("A").getbbox()
    return result.crop(box) if box else result


def checks():
    from PIL import ImageDraw
    mask = Image.new("RGBA", (240, 700), (255, 255, 255, 0))
    draw = ImageDraw.Draw(mask)
    draw.rectangle((80, 25, 160, 200), fill=(20, 40, 10, 255))
    draw.rectangle((35, 200, 205, 670), fill=(20, 40, 10, 255))
    records = []
    for angle in [0, 2, 20, 87, 90, 179, 180, 267, 270]:
        im = mask.rotate(angle, Image.Resampling.NEAREST, expand=True)
        box = im.getchannel("A").getbbox()
        im = im.crop(box)
        best, audit = best_angle(im)
        out = transform(im, best)
        assert out.width * out.height <= im.width * im.height * 1.025
        records.append({"input_angle": angle, "best": best,
                        "run3": policy_angle(best, "iou-min5"), "run4": policy_angle(best, "iou-cardinal5")})
    assert policy_angle(4.99, "iou-min5") == 0
    assert policy_angle(5., "iou-min5") == 5
    assert policy_angle(87., "iou-cardinal5") == 0
    assert policy_angle(178., "iou-cardinal5") == 0
    assert policy_angle(-88., "iou-cardinal5") == 0
    return records
