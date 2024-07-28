{ pkgs }: {
  deps = [
    pkgs.python310Full
    pkgs.python310Packages.python-telegram-bot
    pkgs.calibre
  ];
}
