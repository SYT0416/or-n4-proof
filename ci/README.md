# CI：n=4、α≥8/7 的“cvc5 证明 + Carcara 独立核验”

目标：在 Linux CI 上对 008 的安全区编码（`m=8..12`）逐个产出 cvc5 的 Alethe 证明，并用
独立检查器 Carcara 核验，得到可复现的 `carcara check` PASS，作为定理计算机辅助部分的可机检工件。

## 文件

- `ci/dump_smt2.py`：**自足**的 SMT-LIB 导出器（仅 Python 标准库，无 pip 依赖，不 import 仓库模块）。
  `python ci/dump_smt2.py --m 8 > m8.smt2`。语义与 `src/ffd_safe_region.py::decide(m)` 完全一致
  （排序/区间、忠实 first-fit FFD、MMS≤1、见证指派、秩计数 FFV）；只是把 z3 的 `let`/`Sum` 换成
  扁平 `(+ ...)`/内联，属格式差异。stderr 打印 `variables=… constraints=…` 供人工比对。
- `.github/workflows/verify.yml`：一键 CI（`ubuntu-latest`）。
- 本 README。

## CI 步骤

1. `checkout` + `setup-python`（3.12）。
2. `dtolnay/rust-toolchain@stable`（Carcara 需 Rust ≥ 1.88，stable 满足）。
3. `cargo install carcara --locked`（编译安装独立检查器）。
4. 下载官方 cvc5 1.4.2 Linux static 包并加入 PATH。
5. 对 `m=8..12`：
   - `python ci/dump_smt2.py --m m > m.smt2`，记录 sha256；
   - `cvc5 --produce-proofs --proof-format-mode=alethe --dump-proofs --tlimit=600000 m.smt2`
     输出 `unsat` + Alethe 证明；去掉首行 `unsat` 得 `m.alethe`，记录 sha256；
   - `carcara check --allow-int-real-subtyping m.alethe` 独立核验。
6. `upload-artifact` 上传全部 `m*.smt2`、`m*.alethe`、`*.sha256`、`cvc5-*.log`。

## 参数说明

- **`--allow-int-real-subtyping`**：编码里 0/1 计数是 Int（如 `(+ (ite a 1 0) …)`），物品尺寸是 Real
  （`(+ (ite g x 0.0) …)`），二者经 `=`/`≤` 比较形成 Int/Real 混合；Carcara 需允许该子类型转换。
- **`--proof-format-mode=alethe`**：cvc5 1.4.2 的可外部核验格式（Carcara 只认 Alethe）。
- **`tail -n +2`**：cvc5 先打印一行 `unsat`，其后才是证明；去掉该行即得纯 Alethe 证明。
- **`--tlimit=600000`**：单实例 10 分钟上限（m=12 可能较慢；如不够可在 workflow 调大）。

## 产物与判定

- 若 5 个 `carcara check` 全 PASS → 得到“完备（m=8..12 逐项）机器核验工件”，
  主定理的计算机辅助部分可升级描述为“cvc5 产证明 + Carcara 独立核验（PASS）”。
- 若某 `carcara check` FAIL → 编码/证明链有问题，需回查（可能是 cvc5 与 Carcara 的规则名/子类型差异，
  调整 workflow 参数后重跑）。

## 本地自测（Windows 上）

- 本地已装 cvc5：`cvc5 <(python ci/dump_smt2.py --m 8)` 应与 010 的 `logs/safe_region_m8.smt2`
  同样返回 `unsat`（语义一致性）。
- Carcara 在本地未装（Rust 已装但缺 MSVC 链接器），故 `carcara check` 只能在 CI（Linux）复现。
