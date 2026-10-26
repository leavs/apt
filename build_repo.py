"""Collect registered public Releases and publish a signed multi-package APT repo."""
import gzip
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import subprocess


def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def main():
    os.chdir(Path(__file__).resolve().parent)
    fingerprint = os.environ["APT_SIGNING_FINGERPRINT"]
    expected = Path("keys/apt-key.fingerprint").read_text().strip()
    if fingerprint != expected:
        raise ValueError("Signing key differs from committed fingerprint")
    build = Path("build")
    if build.exists():
        shutil.rmtree(build)
    site = build / "site"
    pool = site / "pool/main"
    pool.mkdir(parents=True)
    registered = json.loads(Path("packages.json").read_text())["sources"]
    seen = set()
    rows = []
    for index, source in enumerate(registered):
        repository = source["repository"]
        release = json.loads(run("gh", "release", "view", "--repo", repository,
                                 "--json", "tagName,url"))
        downloads = build / "downloads" / str(index)
        downloads.mkdir(parents=True)
        subprocess.run(["gh", "release", "download", release["tagName"], "--repo", repository,
                        "--pattern", "*.deb", "--pattern", "*.deb.sha256",
                        "--dir", str(downloads)], check=True)
        found = set()
        for package in sorted(downloads.glob("*.deb")):
            checksum = package.with_name(package.name + ".sha256")
            digest = hashlib.sha256(package.read_bytes()).hexdigest()
            if not checksum.exists() or checksum.read_text().split()[0] != digest:
                raise ValueError(f"Missing or invalid checksum: {package.name}")
            name = run("dpkg-deb", "--field", str(package), "Package")
            arch = run("dpkg-deb", "--field", str(package), "Architecture")
            version = run("dpkg-deb", "--field", str(package), "Version")
            if name not in source["packages"] or arch not in {"amd64", "arm64", "all"}:
                raise ValueError(f"Unregistered package or architecture: {name} {arch}")
            identity = name, arch
            if identity in seen:
                raise ValueError(f"Duplicate package: {identity}")
            seen.add(identity)
            found.add(name)
            shutil.copyfile(package, pool / package.name)
            rows.append((name, version, arch, release["url"]))
        if found != set(source["packages"]):
            raise ValueError(f"Missing registered packages from {repository}")

    # Leave room below the GitHub Pages 1 GB published-site limit.
    if sum(p.stat().st_size for p in pool.iterdir()) > 900_000_000:
        raise ValueError("APT packages exceed 900 MB; reduce packages or move hosting")
    metadata = run("apt-ftparchive", "packages", "pool", cwd=site)
    for arch in ("amd64", "arm64"):
        binary = site / "dists/stable/main" / f"binary-{arch}"
        binary.mkdir(parents=True)
        paragraphs = [p for p in metadata.split("\n\n")
                      if any(line in {f"Architecture: {arch}", "Architecture: all"}
                             for line in p.splitlines())]
        data = (("\n\n".join(paragraphs) + "\n\n") if paragraphs else "").encode()
        (binary / "Packages").write_bytes(data)
        (binary / "Packages.gz").write_bytes(gzip.compress(data, mtime=0))
    options = {"Origin": "leavs Tools", "Label": "leavs Public Tools",
               "Suite": "stable", "Codename": "stable", "Architectures": "amd64 arm64",
               "Components": "main"}
    args = ["apt-ftparchive"]
    for key, value in options.items():
        args.extend(["-o", f"APT::FTPArchive::Release::{key}={value}"])
    release = subprocess.check_output([*args, "release", "dists/stable"], cwd=site)
    (site / "dists/stable/Release").write_bytes(release)
    public_key = subprocess.check_output(["gpg", "--batch", "--export", fingerprint])
    if public_key != Path("keys/apt-key.gpg").read_bytes():
        raise ValueError("Exported public key differs from committed key")
    (site / "apt-key.gpg").write_bytes(public_key)
    for mode, output in (("--clearsign", "InRelease"), ("--detach-sign", "Release.gpg")):
        subprocess.run(["gpg", "--batch", "--yes", "--armor", "--local-user", fingerprint,
                        "--digest-algo", "SHA256", mode, "--output", str(site / "dists/stable" / output),
                        str(site / "dists/stable/Release")], check=True)
    subprocess.run(["gpgv", "--keyring", str((site / "apt-key.gpg").resolve()),
                    str(site / "dists/stable/InRelease")], check=True)
    listing = "\n".join(f'<tr><td>{html.escape(n)}</td><td>{html.escape(v)}</td>'
                         f'<td>{a}</td><td><a href="{html.escape(url)}">Release</a></td></tr>'
                         for n, v, a, url in rows)
    template = Path("index.html").read_text()
    (site / "index.html").write_text(template.replace("<!-- PACKAGES -->", listing))
    (site / ".nojekyll").touch()
    print("Signed shared APT repository ready: build/site")


if __name__ == "__main__":
    main()
