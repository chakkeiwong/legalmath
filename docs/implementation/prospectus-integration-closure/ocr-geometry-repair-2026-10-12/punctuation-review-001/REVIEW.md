# Two punctuation corrections, independently reinspected

The retained 300 dpi page images were cropped around the affected words and
visually reinspected before corrected P1 consumption. Page 176 reads `S.A.`;
its worker token is `S.A,`. Page 178 reads `Lisboa,`; its worker token is
`Lisboa.`. These are recognition errors. The pre-OCR image oracle is unchanged.
The crops retain their original pixels, without rescaling or enhancement.

Use two occurrence-specific, image-bound P1 correction maps. Preserve all raw
characters, coordinates and qualifications. Corrected display segments receive
no bounding box. The report-scope consumer continues quoting the raw reading;
its answer also retains the P1 corrections. Report 9/11 raw passage matches and
11/11 only if the separately corrected display passes. Do not call this
automatic correction or silently substitute corrected text into raw quotations.
The assurance classification REASONABLE is a supplied translation judgment for
`grau de segurança aceitável`, not a result of string matching.

The first crop command used the application interpreter, which lacks Pillow;
it failed at import before producing files. The corrected command used the
existing `tfgpu` interpreter with `CUDA_VISIBLE_DEVICES=-1`. No install or GPU
call occurred. Source images and model remain bound by the original manifest.
