# Local image-review environment correction

The initial optional lossless crop command used `.venv/bin/python` and failed
before writing any file with `ModuleNotFoundError: No module named 'PIL'`.
The original 300dpi rendering had already succeeded and was retained unchanged.
The reviewed native environment `/home/chakwong/miniconda3/envs/tfgpu/bin/python`
contains Pillow; using it with `CUDA_VISIBLE_DEVICES=-1` produced the crops.
No dependency was installed, OCR launched, or model loaded by either crop command.
This consumes the package's one local implementation/environment repair allowance.
The failure concerns the image-review helper's interpreter choice, not OCR quality.

Crop pixel rectangles: upper-left [310,465,1050,755]; default-titles-edge
[1550,470,3070,570]; lower-left [310,1530,1110,1830]; prepayment-title-edge
[1550,1545,3070,1645]; default-lower-left [310,840,1050,950];
default-lower-title [1550,840,2250,950]; prepayment-upper-left
[310,1195,1050,1300]; prepayment-upper-title [1550,1195,2250,1300].
All are exact pixel crops of page-84-300dpi.png; no resampling or OCR correction.
