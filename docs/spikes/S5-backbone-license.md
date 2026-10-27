# S5: Backbone licensing for glyph-crop clustering

## Verdict
DINOv3: **yes-with-conditions**. Recommended: **DINOv2 ViT-S/14 (facebook/dinov2-small, Apache-2.0)** as primary; DINOv3 ViT-S/16 as optional comparison only.
Reason: DINOv3 License is custom (not OSI, not CC/MIT compatible as a label), gated, and carries pass-through terms. Publishing embeddings/clusters appears allowed, but DINOv2 gives the same capability with zero friction and no gate for repo users to reproduce.

## Comparison
| | DINOv3 | DINOv2 | SigLIP 2 |
|---|---|---|---|
| License | "DINOv3 License" (Meta custom, 2025-08-19) | Apache-2.0 (HF tag) | Apache-2.0 (HF tag) |
| Gated | Yes (HF: must agree to share HF info; terms accepted on login) | No | No |
| Redistribute weights | Only with copy of Agreement | Apache terms | Apache terms |
| Publish derived embeddings | Appears allowed; must acknowledge use in publication | Yes | Yes |
| Restrictions | No reverse engineering; Trade Controls / military end-use prohibited; Meta may terminate on breach; California law | none beyond Apache | none |
| HF ids | facebook/dinov3-vits16-pretrain-lvd1689m (also torch hub via repo, needs signed URLs from request form) | facebook/dinov2-small; torch.hub facebookresearch/dinov2 | google/siglip2-base-patch16-224 (and collection) |
| Smallest | ViT-S/16, 21.6M params, dim 384, 4 registers | ViT-S/14, 22.1M, dim 384 | base only seen: HF shows 0.4B total (includes text tower; vision tower ~86M, from memory) |
| Patch / res | 16; any multiple of 16 (RoPE) | 14; pos-embed interpolated, default pipeline 224 | 16; fixed 224 (naflex variants exist, unchecked) |
| Small-crop upscale | Yes: 30-80 px crops -> pad/resize to 112-224 | Same (e.g. 126 or 224) | Same, 224 fixed |
| Handwriting evidence | none found | none verified; generic SSL features commonly used for retrieval | none found |

## Evidence
- DINOv3 LICENSE: https://raw.githubusercontent.com/facebookresearch/dinov3/main/LICENSE.md
  - 1.a: "non-exclusive, worldwide, non-transferable and royalty-free limited license". No non-commercial clause found.
  - 1.b.i: "you shall provide a copy of this Agreement with any such DINO Materials."
  - 1.b.ii: "you must acknowledge the use of DINO Materials in your publication."
  - 1.b.iv-v: no reverse engineering; "end uses prohibited by Trade Controls, including those related to military or warfare purposes".
  - 5.a: "you are and will be the owner of such derivative works and modifications."
  - 6: Meta may terminate on breach. 7: California law.
- DINOv3 HF card: https://huggingface.co/facebook/dinov3-vits16-pretrain-lvd1689m (license tag dinov3-license; gated; 21.6M; patch 16)
- DINOv2: https://huggingface.co/facebook/dinov2-small (Apache-2.0, 22.1M, not gated)
- SigLIP 2: https://huggingface.co/google/siglip2-base-patch16-224 (Apache-2.0, not gated)

## Unverified
- License text came through a summarizing fetch; quotes are from that output, not a full read. Read LICENSE.md directly before relying on any clause. Not checked: whether embeddings count as "DINO Materials" or "Outputs" (5.a suggests derivative works are owner's, but CC BY 4.0 relicensing of embeddings is a legal judgment).
- Whether the repo may host DINOv3 weights under MIT (needs copy of Agreement; do not bundle, link instead).
- DINOv2 patch size 14 / default res 224 from memory, not the card. DINOv2 weights were historically CC-BY-NC; HF tag now says Apache-2.0 but verify the repo LICENSE and weights notice.
- SigLIP 2 vision-only param count and smaller variants; NaFlex variants.
- No searches done for handwriting/glyph SSL evidence; "none found" means not looked for beyond the cards.
- Apache-licensed MAE/iBOT checkpoints not investigated.
