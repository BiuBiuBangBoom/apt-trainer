# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 地面规则

- 遇到不确定的需求时，不要自己猜测和决定实现方案，必须先向用户确认。宁可多问一句，也不要自作主张加一个用户不需要的功能。

## 运行

```bash
conda activate python313
python main.py            # 正常运行
python main.py -n 20      # 限制 20 题
python main.py -t 30      # 每题限时 30s

python -m unittest test_all -v   # 运行测试
```

## 代码风格

- Python 3.13，纯标准库，**零外部依赖**
- 所有函数/方法使用类型标注（含 `Optional`、`list[...]`、`dict[...]`）
- 数据容器用 `@dataclass`，不写手写 `__init__`
- 抽象基类继承 `ABC`，`@abstractmethod` 方法体用 `...` 不用 `pass`
- 内部方法单下划线前缀（`_generator`、`_escape`、`_build_prompt`）
- 模块级 `__all__` 不需要，导入按需取用
- import 顺序：标准库 → 本地模块，每组之间空一行
- 变量命名惯例：`q` = Question, `qt` = QuestionType, `r` = Record, `ds` = DataStore, `feats` = features, `recs` = records
- 用户可见字符串用中文，代码标识符用英文
- 默认不写注释；只在 WHY 不明显时才加一行短注释

## 项目规则

- `settings.json` 已加入 `.gitignore`，不要提交它
- `data/` 目录也已忽略，运行期生成的数据不要提交
- 修改 `QuestionType` 子类时，同步更新 `test_all.py` 中对应的测试
- `Question` dataclass 的 `meta` 字段是 `dict`，调用方用 `meta.get()` 取值，不要假设 key 一定存在

## 安全红线

- API key 只通过 `settings.json` 的 `api_key` 字段或环境变量 `DEEPSEEK_API_KEY` 传入，**绝不硬编码**
- 不要在任何地方 `print` API key
- LLM 返回内容用于展示，不要直接 eval/exec
