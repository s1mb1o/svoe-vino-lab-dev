"""Train an Ultralytics YOLO for one class (bottle) on the phone's portrait frames.

    python train_yolo.py MODEL DATA.yaml [--epochs 60] [--imgsz 800] [--batch 16] [--name NAME]
                         [--check PHOTOS.yaml]

--check validates the best weights once more on another set (the reviewed photos).

The frames are 9:16; training is square (mosaic), while export and the phone run a
rectangular 800x448 input.
"""

import argparse

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("data")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=800)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--name", default=None)
    parser.add_argument("--check", default=None)
    args = parser.parse_args()
    short = args.epochs < 10
    model = YOLO(args.model)
    model.train(
        data=args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, workers=4,
        project="D:/shelfreid/runs", name=args.name or args.model.split(".")[0], exist_ok=True,
        warmup_epochs=1 if short else 3, close_mosaic=1 if short else 10,
        degrees=5.0, shear=1.0, mixup=0.0, fliplr=0.5, plots=False, verbose=False)
    best = YOLO(str(model.trainer.best))
    for title, data in (("val", args.data), ("check", args.check)):
        if data:
            m = best.val(data=data, imgsz=args.imgsz, batch=8, rect=True, plots=False, verbose=False).box
            print(f"RESULT {title}: P {m.mp:.3f} R {m.mr:.3f} mAP50 {m.map50:.3f} mAP50-95 {m.map:.3f} ({model.trainer.best})",
                  flush=True)


if __name__ == "__main__":
    main()
