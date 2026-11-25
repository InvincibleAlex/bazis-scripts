# Native furniture source inspection

Verified read-only on 2026-11-25. BZ85 parsing is experimental and only accepts compressed node streams consumed in full; native enum and object type codes are preserved without assigning guessed meanings.

- `\\RG\Bazis\Accessories\Pins\Pin_8х30.f3d`: parsed 3,316-byte native stream. Model contains framing and two named hole definitions. No TriData node in this parsed stream. This is a candidate library asset, not an established exact source mapping for the current DL830 instances.
- `\\RG\Bazis\Fragments\Hinge Sensys 8639i TH52 110gr., overlay + 3mm.f3d`: parsed 109,635-byte stream. FurnList holds three TriData blocks (56,601 / 18,521 / 26,585 bytes), referenced by object FastID. Includes hinge article 9071205; this is NOT current hinge 9073567. Blob presence is verified, triangle decoding/topology is not.
- Saved test model `00. Mobilier Magazin - Front 1.b3d`: parsed entire 33,295,643-byte native stream. DL830 instance UID 23818 refers to FastID 2067293931; its FurnList entry has ParamType 3, ParData/Elements, native holes and bounds, no TriData. Hinge 9073567 entry F1867166506 has ParamType 4, ParData/Elements referring to screws 10085, mounting plate 9075005 and hinge 9073567, native holes and bounds, no TriData. Type-code geometry semantics remain unverified.

Conclusion: saved sources can contain shared mesh data separate from instances, but exact sampled hardware definitions are parametric. Neither a hole radius nor a different hinge mesh should be substituted for confirmed hardware geometry. Native temporary-clone Build/FullBuild/FillElements probes returned zero triangle lists for both tested instances.

Inspector: `tools/inspect_furniture_source.py`. This is an offline diagnostic, not a production solid decoder and not yet wired into MCP. No source asset or model was edited.
