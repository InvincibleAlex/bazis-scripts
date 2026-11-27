# Official EGGER CAD textures

Downloads the public CAD image explicitly associated with an exact decor and finish on the official EGGER page. It rejects ambiguous matches, unrelated domains and restricted downloads. No guessing from lifestyle photographs or search thumbnails.

Requires a complete Python 3.11+ installation with Pillow and working HTTPS certificate support. The existing PDF portable runtime is not a validated network runtime for this tool. HTTPS certificate verification remains enabled. Windows certificate stores are used through Python SSL defaults.

```powershell
python egger_textures.py --code U705 --finish ST9 --texture-root "\\SERVER\Textures"
```

Images are stored under `Egger/Official`, with a source record containing official URLs, SHA-256, pixel dimensions and source DPI. No existing image is overwritten. Non-ST finishes require an explicit official `--page-url`, still checked against exact decor/finish metadata.

## Orientation and scale

The source bitmap is not rotated, mirrored or stretched; the aspect ratio and available ICC/DPI information are retained. The source record's `repeat_mm` is calculated from source pixel dimensions and DPI, not from sheet stock dimensions. It is a proposed physical repeat requiring validation against the manufacturer's decor data and the target application's mapping.

Existing BAZIS rotation, mirroring and physical repeat settings must be inspected before using a newly downloaded texture. A solid colour cannot validate grain direction; use a woodgrain sample. Image orientation and a panel's native grain orientation are separate settings.

## Optional link to an existing material

`--link-material ID --reader-script PATH --backup-dir PATH` is an explicit database write. It requires the already configured private material reader and backs up the old texture row before changing one exact material. It permits PAL only, rejects 16 mm, requires an exact article/finish match and preserves existing physical scale and orientation settings. It does not create or delete materials. Do not run this option until those preserved settings have been validated for the downloaded image.

Credentials and database configuration are never stored in this script. Keep download source records, backups and manufacturer images outside Git. The MIT code license does not relicense EGGER's image assets.

```powershell
python -m unittest discover -s tests -p 'test_egger_textures.py'
```
