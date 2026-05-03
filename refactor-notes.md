# 架构重构记录

## 改了什么、为什么、怎么改

---

### 1. 并行列表 → 单一 dataclass 列表

**原来：**
```python
self._questions: list[str] = []
self._answers: list[str] = []
self._responses: list[str] = []
self._cost_times: list[int] = []
```
四个列表靠同一个索引隐式关联。`_questions[3]` 对应 `_answers[3]` 对应 `_responses[3]`——索引一旦在 append 时错位（比如异常提前退出、代码重构引入 bug），就会静默地把答案 B 判给题目 A，用户莫名其妙。

**现在：**
```python
@dataclass
class SessionRecord:
    question: Question
    response: str
    cost_time_ms: int

class Session:
    records: list[SessionRecord]  # 一个列表，每行自包含
```
一道题的所有信息（题目、回答、耗时）绑定在一起，不存在错位可能。

---

### 2. `generate_question()` 副作用 → 返回自包含的 `Question`

**原来：**
```python
def generate_question(self) -> str:
    self._num1 = random.randint(11, 99)  # 副作用：写入实例状态
    self._num2 = random.randint(2, 9)
    return f"{self._num1} * {self._num2}"

def generate_answer(self) -> str:
    return str(self._num1 * self._num2)  # 隐式依赖 generate_question 先调用
```
问题：`generate_answer()` 必须紧跟在 `generate_question()` 之后调用，中间不能插入任何代码。这使得类不可重入（不能同时生成两道题），也无法单独测试出题或答题逻辑。

**现在：**
```python
def generate_question(self) -> Question:
    a = random.randint(11, 99)
    b = random.randint(2, 9)
    return Question(text=f"{a} * {b}", answer=str(a * b))
```
题目和答案一次性生成，打包返回。方法调用纯函数——不依赖调用顺序，不修改实例状态。

---

### 3. 命名修正

| 原来 | 现在 | 理由 |
|------|------|------|
| `ModeStrategy` | `ExamStrategy` | 它决定**考试怎么进行**（跑图/跑测/考试），不是"模式" |
| `BaseMode` | `QuestionType` | 它决定**出什么题**（乘法/分数/幂次），不是"模式" |
| `RunningMode` | `PracticeMode` | 跑图=练习 |
| `RunningAndTestMode` | `PracticeAndTestMode` | 跑测=练习+测试 |
| `ExaminationMode` | `ExamMode` | 考试模式 |
| `create_mode()` | `create_question_type()` | 创建的是题型，不是模式 |
| `mode_for_type_name()` | `question_type_for_name()` | 查找的是题型，不是模式 |
| `strategy.set_mode()` | `strategy.set_question_type()` | 设置的是题型 |

"Strategy"和"Mode"在原代码里指向相反的概念维度，新命名让每个词的含义和实际职责一致。

---

### 4. `QuestionType` 瘦身 → 分离 `Session`

**原来** `BaseMode` 同时负责：出题、存答案、存回复、存耗时、判对错、打印统计、错题回顾标记、保存记录。一个类扛了四五个不同生命周期的东西。

原有方法清单：
- `generate_question()` / `generate_answer()` — 出题
- `check_answer()` — 判题
- `generate_and_print_question()` — 打印题目并存储
- `add_response()` — 记录用户回答
- `save_records()` — 持久化
- `load_for_review()` — 回顾模式
- `print_statistics()` — 打印统计
- `question_count()` / `answer_at()` / `cost_time_at()` — 数据访问

**现在**拆成两个：

- **`QuestionType`**（mode.py）——只关心"这道题长什么样"：
  - `generate_question() → Question`
  - `check_answer(question, response) → bool`
  - 无状态，纯逻辑

- **`Session`**（strategy.py）——关心"这一轮做了什么"：
  - `records: list[SessionRecord]`
  - `next_question() → Question | None`
  - `record_response(question, response, cost_ms)`
  - `is_correct(index) → bool`
  - `print_statistics()`
  - `save_records(ds, type_name, mode_name)`

每个类只变一个原因：出题逻辑变了只改 `QuestionType`，统计格式变了只改 `Session`。

---

### 5. `mode_for_type_name` 精确匹配

**原来：**
```python
for cls, name in MODE_REGISTRY.values():
    if name.startswith(type_name):  # "两位数乘一位数" 匹配 "两位数乘一位数 : 12 * 1"
        return cls()
```
外加一个硬编码的 special case：
```python
special = {"现期增长率估算增长量": EstimateGrowth}
```
为什么需要 special case？因为 `EstimateGrowth` 的 `type_name`（"现期增长率估算增长量"）不等于它的 display name 前缀（"估算增长量 : 1234 5.6%"），`startswith` 匹配不到。

**现在：**
```python
for cls, _ in MODE_REGISTRY.values():
    instance = cls()
    if instance.type_name == type_name:
        return instance
```
直接比较实例的 `type_name`，不靠字符串前缀匹配，也不需要硬编码 special case。

---

### 6. 回顾模式 flag → preloaded 参数

**原来：**
```python
self._is_review = False   # 污染 QuestionType 的状态空间
self._review_index = 0

def generate_and_print_question(self):
    if self._is_review:
        # 走回顾分支：从预加载列表取题
    else:
        # 走出题分支：随机生成
```
一个问题：`QuestionType` 不应该知道自己是不是在回顾模式。回顾只是换了数据来源（历史记录 vs 随机生成），出题和判题的逻辑完全相同。用一个 flag 区分本质上是把两个不同的数据源硬塞进同一个类。

**现在：**
```python
class Session:
    def __init__(self, question_type, preloaded=None):
        self._gen = self._generator(preloaded)

    def _generator(self, preloaded):
        if preloaded is not None:
            yield from preloaded    # 回顾：逐个返回历史题目
            return                  # 用完即停
        while True:
            yield self.question_type.generate_question()  # 正常：无限生成

    def next_question(self) -> Question | None:
        try:
            return next(self._gen)
        except StopIteration:
            return None
```
回顾模式通过给 `Session` 传入预加载的 `Question` 列表实现。数据来源变了，但 `QuestionType` 完全不知情——它还是只负责 `generate_question()` 和 `check_answer()`。

调用方（main.py）的使用方式：
```python
# 正常模式
session = Session(question_type)

# 回顾模式
questions = [Question(text=r.question, answer=r.answer) for r in to_review]
session = Session(question_type, preloaded=questions)
```

---

### 7. 新增测试

`test_all.py`，31 个测试，覆盖：

- **TestModeRegistry**（5 个）：注册表完整性、创建有效/无效题型、名称查找精确匹配、未知名称
- **TestTwoDigitsTimesOneDigit**（3 个）：type_name、题目生成范围、判对/判错
- **TestOneDigitPlusOneDigit**（1 个）：加法结果范围（11-18）
- **TestOneDigitTimesOneDigit**（1 个）：乘法操作数范围
- **TestThreeDigitsDivideTwoDigits**（1 个）：除法答案为首位非零数字
- **TestFractionCompare**（2 个）：题目格式、符号匹配判题
- **TestPercentageConvertToFraction**（2 个）：百分比格式、正确答案判对
- **TestThreeDigitsTimesOneDigit**（1 个）：三位数乘一位数范围
- **TestEstimateGrowth**（3 个）：精确答案、1% 容差范围内、非法输入
- **TestTwoDigitsSubOneDigit**（1 个）：两位数减一位数格式
- **TestPowerNumber**（1 个）：幂次数 base/exp 范围
- **TestSession**（5 个）：正常生成、记录回复判对、判错、preloaded 耗尽、空 preloaded
- **TestDataStore**（3 个）：转义往返、格式化往返、非法行解析

运行方式：
```bash
conda activate python313
python -m unittest test_all -v
```

---

## 数据流变化对比

### 原来

```
main.py → Context.set_strategy(ModeStrategy)
       → ModeStrategy.set_mode(BaseMode)
       → BaseMode.generate_question()  # 写入 self._num1, self._num2
       → BaseMode.generate_answer()    # 读取 self._num1, self._num2
       → BaseMode.generate_and_print_question()  # 追加到 _questions, _answers
       → ModeStrategy.process_input()  # 追加到 _responses, _cost_times
       → BaseMode.check_answer(index)  # 按索引读取 _responses[index], _answers[index]
       → BaseMode.print_statistics()   # 遍历四个并行列表
       → BaseMode.save_records()
```

### 现在

```
main.py → Context.set_strategy(ExamStrategy)
       → ExamStrategy.set_question_type(QuestionType)
       → ExamStrategy.execute():
           Session(QuestionType, preloaded=...)
           loop:
             q = Session.next_question()        # Question(text, answer, meta)
             print(q.text)
             ExamStrategy.process_input(session, q)  # → Session.record_response()
             Session.is_correct(index)           # → QuestionType.check_answer(q, response)
           Session.print_statistics()
           Session.save_records(ds, ...)
```

---

## 文件改动清单

| 文件 | 改动类型 | 行数变化 |
|------|----------|----------|
| `mode.py` | 重写 | 340 → 163 |
| `strategy.py` | 重写 | 112 → 160 |
| `main.py` | 适配新 API | 254 → 249 |
| `context.py` | 类型标注更新 | 24 → 24 |
| `test_all.py` | **新增** | +278 |
| `CLAUDE.md` | 架构文档更新 | 66 → 74 |

`common.py`、`config.py`、`data_store.py` 无改动。
