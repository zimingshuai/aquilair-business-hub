"""一键切换 rubric 评审模型（评审模型名的单一事实源）。

主要 Input：目标模型名——优先级为命令行参数 > 环境变量 ARK_RUBRIC_MODEL > DEFAULT_MODEL。
主要 Output：3 个手维护配置的 provider id 替换 + promptfooconfig.calibration.yaml 重新生成
           （经 gen_calibration.py，其模型名同源于本模块）+ 后续冒烟与对拍提示。
用法：python set_rubric_model.py [新模型名]
说明：promptfoo 0.123 不支持 provider id 的环境变量插值（2026-09-24 实测：字面 ${VAR}
     被原样发给 API 返回 404），故采用「单点默认值 + 本命令同步」而非配置内变量引用。
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

# ===========一、配置与解析==========
# BASE_DIR：本脚本所在目录（evals/promptfoo/），用于拼接待同步配置的路径。
BASE_DIR = Path(__file__).resolve().parent
# DEFAULT_MODEL：默认评审模型（火山方舟，模型名用连字符——点号会 404）。
#   全仓评审模型名的唯一硬编码点：手维护 yaml 由本脚本同步，calibration.yaml 经生成同步。
DEFAULT_MODEL = 'doubao-seed-2-1-pro-260915'
# MANUAL_CONFIGS：含评审模型 provider id 的手维护配置（calibration.yaml 是生成物，不手改）。
MANUAL_CONFIGS = [
    'promptfooconfig.rubric.yaml',
    'promptfooconfig.replay-rubric.yaml',
    'promptfooconfig.gate.yaml',
]
# PROVIDER_ID_RE：匹配 provider id 的 openai:chat:<模型名> 片段（模型名段为方舟命名安全字符集）。
PROVIDER_ID_RE = re.compile(r'openai:chat:[A-Za-z0-9._-]+')


def resolve_model(cli_arg: Optional[str]) -> str:
    """按优先级解析目标评审模型名。

    Args:
        cli_arg: 命令行传入的模型名；未传时为 None。
    Returns:
        解析后的模型名（命令行参数 > 环境变量 ARK_RUBRIC_MODEL > DEFAULT_MODEL）。
    """
    #   1. 命令行参数 > 2. 环境变量 ARK_RUBRIC_MODEL > 3. 单点默认值
    if cli_arg:
        return cli_arg
    return os.environ.get('ARK_RUBRIC_MODEL', DEFAULT_MODEL)


def update_config(config_path: Path, new_model: str) -> bool:
    """替换单个配置文件中的评审模型名并写回。

    Args:
        config_path: 目标配置文件路径。
        new_model: 新模型名。
    Returns:
        文件是否发生变更（与现值一致时不写回，保证幂等重跑无 diff）。
    Raises:
        SystemExit: 配置中未命中 provider id（文件改名或结构变化），提示人工核对。
    """
    #   1. 读原文（newline='' 不做行尾转换，避免 Windows 下 LF 被整体改写成 CRLF 产生全文件 diff）
    with open(config_path, 'r', encoding='utf-8', newline='') as config_file:
        text = config_file.read()
    #   2. 替换 provider id 中的模型名段（行尾注释不受影响）
    replaced, hit_count = PROVIDER_ID_RE.subn('openai:chat:' + new_model, text)
    if hit_count == 0:
        sys.exit('[错误] 未在 {} 找到 openai:chat:<模型>，请人工核对文件结构'.format(config_path.name))
    #   3. 有变化才写回（同样不做行尾转换）
    if replaced != text:
        with open(config_path, 'w', encoding='utf-8', newline='') as config_file:
            config_file.write(replaced)
        return True
    return False


# ===========二、执行入口==========
def main() -> None:
    """执行模型切换：解析目标模型 -> 同步手维护配置 -> 重生成 calibration -> 打印后续步骤。"""
    #   1. 解析目标模型（参数 > 环境变量 > 默认值）
    new_model = resolve_model(sys.argv[1] if len(sys.argv) > 1 else None)
    print('====目标评审模型====: {}'.format(new_model))
    #   2. 同步 3 个手维护配置（幂等：与现值一致则不写）
    for config_name in MANUAL_CONFIGS:
        changed = update_config(BASE_DIR / config_name, new_model)
        print('====配置{}====: {}'.format('已更新' if changed else '无变化', config_name))
    #   3. 重生成 calibration 配置（生成物不手改）；把目标模型经 ARK_RUBRIC_MODEL 注入子进程，
    #     使 gen_calibration 的 resolve_model 解析到同一模型（命令行参数不跨进程传递）
    regen_env = dict(os.environ, ARK_RUBRIC_MODEL=new_model)
    subprocess.run(
        [sys.executable, str(BASE_DIR / 'gen_calibration.py')],
        check=True,
        env=regen_env,
    )
    #   4. 后续必做：冒烟验证 + 重新对拍（换 judge 后门禁资格作废，对拍达标才恢复）
    print('====后续必做====: '
          '① 冒烟 npx promptfoo eval -c promptfooconfig.rubric.yaml --no-cache（预期 2 条方向正确、退出码 0）；'
          '② 重新对拍 npx promptfoo eval -c promptfooconfig.calibration.yaml --no-cache'
          '（正负样本一致率达标后 rubric 才可继续当门禁）')


if __name__ == '__main__':
    main()
