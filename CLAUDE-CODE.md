# CentOS 7.4용 Claude Code 오프라인 번들

기존 VS Code Remote-SSH와 같은 방식으로 인터넷이 되는 PC에서 번들을 만들고, CentOS 서버에는 압축 파일과 체크섬만 옮깁니다. 설치가 끝나면 SSH 세션이나 VS Code Remote-SSH의 원격 터미널에서 `claude`를 실행할 수 있습니다.

| 항목 | 버전 또는 대상 |
| --- | --- |
| Claude Code CLI | `2.1.329` (Anthropic 공식 `linux-x64-musl` 바이너리) |
| 전용 로더 | Debian musl `1.2.5-3.1~deb13u1` |
| 대상 | CentOS 7.4 x86_64, glibc 2.17, Linux 3.10 |

CentOS 7.4는 [Anthropic의 공식 지원 목록](https://code.claude.com/docs/en/setup#system-requirements) 밖에 있습니다. 이 번들은 공식 musl 바이너리와 전용 로더를 함께 설치하는 호환 구성입니다. 런처는 해당 프로세스에서만 로더를 사용합니다. 홈 디렉터리에 쓰기 권한이 있는 일반 계정으로 설치할 수 있으며, `sudo`, 시스템 Node.js, npm, Docker 또는 사용자 네임스페이스는 필요 없습니다.

## 1. 인터넷이 되는 PC에서 생성

Python 3.10 이상이 필요합니다. 저장소 루트에서 실행하세요. Windows에서는 WSL 없이 실행할 수 있습니다.

```powershell
py -3 build_claude_bundle.py
```

```bash
python3 build_claude_bundle.py
```

`dist/`에 `claude-code-2.1.329-centos74-x64.tar.gz`와 `.tar.gz.sha256`가 만들어집니다. 생성기는 공식 바이너리와 Debian 패키지를 다운로드한 뒤 [고정 SHA-256](claude-bundle-lock.json)을 비교합니다. 필요한 로더와 musl 라이선스 고지를 Debian 패키지에서 추출합니다.

## 2. CentOS 서버에서 설치

두 파일을 같은 디렉터리에 옮긴 다음 Claude Code를 사용할 일반 계정으로 실행하세요.
이 버전은 압축 파일, 압축을 푼 폴더, 설치 사본을 함께 두면 약 870 MiB를 사용합니다.

```bash
sha256sum -c claude-code-2.1.329-centos74-x64.tar.gz.sha256
tar -xzf claude-code-2.1.329-centos74-x64.tar.gz
cd claude-code-2.1.329-centos74-x64
bash install.sh
"$HOME/.local/bin/claude" --version
```

설치 스크립트는 체크섬과 CLI의 `--version`, `--help`를 검사한 뒤 `CLAUDE_DOCTOR_OK`를 출력합니다. 설치 파일은 `~/.local/share/claude-code-centos74/versions/<버전>/`에 저장되며, `~/.local/bin/claude`가 해당 버전을 가리킵니다. 그 위치에 다른 Claude Code 실행기가 이미 있으면 설치 스크립트가 기존 실행기를 유지하고 새 실행기의 전체 경로를 출력합니다.

`claude`를 짧게 입력하려면 현재 셸에서 `export PATH="$HOME/.local/bin:$PATH"`를 실행하세요. SSH 세션을 다시 열어도 적용하려면 같은 줄을 `~/.bashrc`에 추가하세요. 이후 설치 상태는 압축을 풀었던 폴더에서 다음 명령으로 다시 확인할 수 있습니다.

```bash
bash doctor.sh "$HOME/.local/share/claude-code-centos74/versions/2.1.329"
```

CentOS 7.4 설치 이미지로 부팅한 가상 머신에서 커널 `3.10.0-693.el7.x86_64`, 시스템 glibc 2.17, 비활성화된 사용자 네임스페이스로 검사했습니다. 네트워크 장치가 없는 상태에서 일반 계정으로 설치와 재설치, 다른 디렉터리에서 설치된 런처 실행, 수동 업데이트 명령의 차단을 확인했습니다.

## 3. 사내 모델에 연결

설치와 시작 검사는 외부 인터넷 없이 가능합니다. 프롬프트를 처리하려면 CentOS에서 접근 가능한 모델 API가 필요합니다. 사내 vLLM이나 게이트웨이가 **Anthropic Messages API `POST /v1/messages`**와 스트리밍을 제공하는 경우에는 아래처럼 실행할 수 있습니다. `ANTHROPIC_BASE_URL`에는 `/v1` 앞까지의 주소를 넣고, 모델명과 인증은 서버 설정에 맞춥니다. [vLLM 연결 예제](https://docs.vllm.ai/en/latest/serving/integrations/claude_code/) · [Anthropic 게이트웨이 규격](https://code.claude.com/docs/en/llm-gateway-protocol)

```bash
export ANTHROPIC_BASE_URL='http://내부-게이트웨이:8000'
export ANTHROPIC_MODEL='서버에-등록된-모델명'
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
# 인증 방식에 따라 ANTHROPIC_AUTH_TOKEN 또는 ANTHROPIC_API_KEY를 설정하세요.
# 인증 없는 vLLM은 vLLM 문서의 dummy 값 예제를 따르세요.
"$HOME/.local/bin/claude" -p '연결 확인용으로 OK만 출력해 줘'
```

사내 Kimi가 `/v1/chat/completions` 또는 `/v1/responses`만 제공한다면 Claude Code 앞에 Messages 형식으로 변환하는 게이트웨이가 필요합니다. 기본 응답이 오면 모델의 도구 호출과 도구 결과 처리까지 사내 서버에서 확인하세요.

## 업데이트

런처는 `DISABLE_UPDATES=1`을 설정해 계속 같은 버전을 사용합니다. 새 버전이 필요하면 [Anthropic의 서명된 매니페스트](https://code.claude.com/docs/en/setup#verify-the-manifest-signature)에서 서명과 `platforms.linux-x64-musl.checksum`을 확인하고 `claude-bundle-lock.json`의 버전, URL, 파일명, 체크섬을 함께 갱신하세요. 새 번들의 기동을 확인한 다음 설치 스크립트가 실행기 링크를 전환합니다.
