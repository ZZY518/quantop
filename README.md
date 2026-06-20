# quantop

quantop 是一个本地开发阶段的金融数据分析 MVP，用 Mock 数据先跑通完整链路：

第三方数据源 -> ODS 原始数据 -> DWD 清洗数据 -> FACTOR 因子数据 -> FastAPI 查询 -> Vue 3 展示。

当前阶段不包含 Docker、云部署、CI/CD、登录权限、复杂回测和机器学习预测。

## 技术栈

- 后端：Python、FastAPI、SQLAlchemy、SQLite、APScheduler、Pandas
- 前端：Vue 3、TypeScript、Vite、ECharts
- 数据库文件：`data/quantop.db`

`data/*.db` 已在 `.gitignore` 中排除，不提交 Git。

## 项目结构

```text
quantop/
  backend/
    app/
      api/
      core/
      data_sources/
      factors/
      jobs/
      models/
      schemas/
      services/
      utils/
    requirements.txt
    run.py
  frontend/
    src/
      components/
      lib/
      views/
    package.json
  scripts/
    init_db.py
  data/
  docs/
```

## 初始化数据库

```bash
cd quantop
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
python scripts\init_db.py
```

初始化后会创建 `data/quantop.db` 和 6 张核心表：

- `stock_basic`
- `trade_calendar`
- `ods_stock_daily`
- `dwd_stock_daily`
- `factor_stock_daily`
- `sync_task_log`

长期行情周期能力新增 3 张统一 bar 表：

- `ods_stock_bar`
- `dwd_stock_bar`
- `factor_stock_bar`

`dwd_stock_bar` 使用 `symbol + period + trade_date` 作为主键，`period` 当前支持 `1d / 1w / 1m`。日线、周线、月线统一走 bar 表，后续分钟线也可以扩展到同一结构。

## 启动后端

```bash
cd quantop\backend
..\.venv\Scripts\activate
python run.py
```

PowerShell 中可使用：

```powershell
cd quantop\backend
..\.venv\Scripts\Activate.ps1
python run.py
```

后端地址：

- API: `http://127.0.0.1:8000/api`
- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/health`

如需手动启动 APScheduler：

```bash
python run.py --scheduler
```

默认不自动启动调度器。

## 执行同步任务

可在 Swagger 中调试，也可使用 curl：

```bash
curl -X POST "http://127.0.0.1:8000/api/sync/run?limit=10"
```

同步逻辑：

- `stock_basic` 使用 `symbol` 幂等写入。
- `ods_stock_daily` 保存 Mock 源返回的原始 JSON 字符串。
- `dwd_stock_daily` 使用 `symbol + trade_date` UPSERT。
- `factor_stock_daily` 使用 `symbol + trade_date` UPSERT。
- 每次同步都会写入 `sync_task_log`。
- `stock-daily/top-amount` 会按数据源提供的成交额排名选择股票池，再批量同步日线；当前 Mock 源只有测试股票，接真实数据源后可扩展为市场成交额 Top N。
- `sync/bars` 会把 `1d` 日线聚合为 `1w / 1m` 周线和月线。
- `sync/bar-factors` 会按指定周期计算 MA、RSI、MACD、收益率、波动率和评分。

## 启动前端

```bash
cd quantop\frontend
npm install
npm run dev
```

前端地址：

```text
http://127.0.0.1:3000
```

如后端地址不是默认值，可设置：

```bash
VITE_API_BASE=http://127.0.0.1:8000/api npm run dev
```

## API 示例

```bash
curl http://127.0.0.1:8000/api/stocks
curl http://127.0.0.1:8000/api/stocks/600519.SH
curl http://127.0.0.1:8000/api/stocks/600519.SH/daily
curl http://127.0.0.1:8000/api/stocks/600519.SH/factors
curl "http://127.0.0.1:8000/api/stocks/600519.SH/chart?period=1d"
curl "http://127.0.0.1:8000/api/stocks/600519.SH/chart?period=1w"
curl "http://127.0.0.1:8000/api/stocks/600519.SH/bars?period=1m"
curl "http://127.0.0.1:8000/api/stocks/600519.SH/bar-factors?period=1m"
curl "http://127.0.0.1:8000/api/market/rank?limit=10"
curl "http://127.0.0.1:8000/api/market/rank?rank_type=score&limit=10"
curl http://127.0.0.1:8000/api/sync/logs
```

## 数据源配置

当前支持 `akshare` 和 `baostock` 两个数据源，默认使用 `akshare`：

```powershell
$env:QUANTOP_DATA_SOURCE="akshare"
python backend\run.py
```

切换 Baostock：

```powershell
$env:QUANTOP_DATA_SOURCE="baostock"
python backend\run.py
```

AKShare 支持成交额榜接口，适合作为默认同步源。Baostock 主要提供历史行情，没有现成的实时成交额榜；项目会基于最近交易日股票池逐只查询日线成交额后排序，因此同步 Top N 会比 AKShare 慢。
