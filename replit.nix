{pkgs}: {
  deps = [
    pkgs.zip
    pkgs.rustc
    pkgs.pkg-config
    pkgs.libxcrypt
    pkgs.libiconv
    pkgs.cargo
    pkgs.openssl
  ];
}
