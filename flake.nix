{
  description = "WGUPS Routing Program — C950 Task 2";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forEachSystem = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forEachSystem (pkgs: {
        default = pkgs.mkShell {
          name = "wgups-routing";
          buildInputs = [
            pkgs.python312
            pkgs.pypy3
            pkgs.pyright
            pkgs.ruff
            pkgs.just
            pkgs.git
          ];
          shellHook = ''
            echo "WGUPS Routing Program dev shell ready"
            echo "  python  : $(python --version)"
            echo "  pypy3   : $(pypy3 --version)"
            echo "  just    : $(just --version)"
            echo "  ruff    : $(ruff --version)"
            echo "  pyright : $(pyright --version)"
          '';
        };
      });
    };
}
