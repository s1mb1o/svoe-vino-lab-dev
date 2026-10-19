"""YOLOX-s for one class (bottle) on the portrait frames of a phone: the input keeps the
9:16 of the frame (448x800), so a bottle far away stays big enough to find.

    python tools/train.py -f yolox_s_bottle.py -d 1 -b 16 --fp16 -c weights/yolox_s.pth
"""

import os

from yolox.exp import Exp as BaseExp


class Exp(BaseExp):
    def __init__(self):
        super().__init__()
        self.depth = 0.33
        self.width = 0.50
        self.num_classes = 1
        self.input_size = (800, 448)   # height, width
        self.test_size = (800, 448)
        self.multiscale_range = 3      # +-3 x 32 px on the height while training
        self.data_dir = os.environ.get("SHELFREID_DATA", "D:/shelfreid/data/trial")
        self.train_ann = "train.json"
        self.val_ann = os.environ.get("SHELFREID_VAL_ANN", "val.json")
        self.max_epoch = int(os.environ.get("SHELFREID_EPOCHS", 60))
        self.warmup_epochs = min(3, max(1, self.max_epoch // 10))
        self.no_aug_epochs = min(10, max(1, self.max_epoch // 6))
        self.eval_interval = int(os.environ.get("SHELFREID_EVAL_EVERY", 5))
        self.data_num_workers = 4
        self.mosaic_scale = (0.5, 1.5)
        self.enable_mixup = False      # mixed bottles from two shelves teach nothing a shelf shows
        self.degrees = 5.0             # a phone held almost upright
        self.shear = 1.0
        self.test_conf = 0.01
        self.nmsthre = 0.5
        self.exp_name = os.path.splitext(os.path.basename(__file__))[0]
