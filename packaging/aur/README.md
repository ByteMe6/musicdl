# AUR package

The [`trackfetch`](https://aur.archlinux.org/packages/trackfetch) AUR package is built from this folder.

## First publish

1. Create an account at <https://aur.archlinux.org/register>.
2. In **My Account**, paste your public key (`cat ~/.ssh/id_ed25519.pub`) into **SSH Public Key** and save.
3. Push the package:

```bash
git clone ssh://aur@aur.archlinux.org/trackfetch.git aur-trackfetch
cp PKGBUILD .SRCINFO aur-trackfetch/
cd aur-trackfetch
git add PKGBUILD .SRCINFO
git commit -m "Initial upload: trackfetch 2.0.0"
git push
```

## Updating for a new release

After a new `vX.Y.Z` release is published on GitHub, set `pkgver=X.Y.Z` and `pkgrel=1` in `PKGBUILD`, then run:

```bash
updpkgsums                          # from pacman-contrib: refreshes sha256sums
makepkg -si                         # build, run the tests, install
makepkg --printsrcinfo > .SRCINFO
```

Copy both files into your `aur-trackfetch` clone, commit as `Update to X.Y.Z` and push.

`namcap` reports `deno`, `ffmpeg` and `yt-dlp` as possibly unneeded. They are needed: trackfetch runs them as external programs, which namcap can't detect.
