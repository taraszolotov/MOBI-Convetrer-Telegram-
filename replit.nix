{ pkgs }: {
  deps = [
    pkgs.python38Full
    pkgs.python38Packages.pip
    pkgs.python38Packages.setuptools
    pkgs.python38Packages.wheel
  ];
}
