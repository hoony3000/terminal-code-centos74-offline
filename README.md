# CentOS 7.4용 VS Code Remote-SSH 오프라인 번들

오프라인 PC의 Microsoft VS Code 데스크톱으로 오프라인 CentOS 7.4 x86_64에 SSH 접속하는 구성입니다. 인터넷이 되는 Windows 또는 Linux PC에서 두 설치 파일을 만들고, 각각의 대상 머신에 옮깁니다.

| 항목 | 고정 버전 |
| --- | --- |
| Microsoft VS Code 데스크톱과 서버 | `1.146.0 Stable` |
| 빌드 커밋 | `69047191fc427f2f92828279aae1d90d8eeda7ab` |
| Remote - SSH | `0.128.0` |
| Microsoft 서버 내장 Node.js | `24.22.1` |
| CentOS용 전용 런타임 | Ubuntu glibc `2.31-0ubuntu9.18`, GCC 10.5 C++ 런타임, `patchelf 0.18.0` |

Microsoft의 공식 서버 요구사항은 Linux 커널 4.18 이상입니다. CentOS 7.4의 3.10 커널에서는 전용 런타임을 적용하는 시험 구성이며, 도입 전에 실제 서버에서 아래 검증을 마쳐야 합니다. [Microsoft 요구사항과 전용 런타임 문서](https://code.visualstudio.com/docs/remote/faq#_can-i-run-vs-code-server-on-older-linux-distributions)

## 1. 인터넷이 되는 머신에서 번들 만들기

Python 3.10 이상이 필요합니다. Windows에서 WSL 없이 실행할 수 있습니다. 접속 PC의 OS에 맞는 `--client` 값을 지정하세요. 생성기를 실행하는 OS와 접속 PC의 OS는 서로 달라도 됩니다.

```powershell
# Windows에서 Windows 접속 PC용 번들 생성
py -3 build_bundle.py --client windows-x64
```

```bash
# Linux에서 Linux 접속 PC용 번들 생성
python3 build_bundle.py --client linux-x64
```

`dist/`에 `vscode-1.146.0-client-<대상>.zip`, `vscode-1.146.0-server-centos74-x64.tar.gz`, 각 체크섬이 만들어집니다. 공식 다운로드 파일은 `.bundle-cache/`에 캐시되며, 재실행할 때도 SHA-256을 확인합니다. Microsoft 서버 압축파일은 Node와 라이선스 고지를 포함한 공식 원본 형태로 동봉됩니다.

## 2. CentOS 7.4에서 서버 설치

`vscode-1.146.0-server-centos74-x64.tar.gz`를 옮긴 뒤 **VS Code의 SSH 로그인에 사용할 일반 사용자**로 실행합니다.

```bash
tar -xzf vscode-1.146.0-server-centos74-x64.tar.gz
cd vscode-1.146.0-server-centos74-x64
bash install.sh
```

`install.sh`는 번들 체크섬을 확인하고, 공식 서버와 전용 런타임을 `~/.vscode-server/bin/<커밋>/`에 함께 설치합니다. 공식 서버에 포함된 Node의 ELF 로더와 라이브러리 경로를 수정합니다. 시스템 Node 설치, `sudo`, 시스템 glibc 업데이트, 셸 시작 파일 편집은 필요 없습니다. 동일한 번들은 다시 실행해도 설치 상태를 진단할 수 있으며, 같은 커밋 위치에 다른 설치가 있으면 경로를 출력하고 중단합니다.

마지막에 `SERVER_DOCTOR_OK`가 나오면 그 CentOS에서 Node, VS Code 서버 버전, ripgrep과 내장 터미널용 PTY의 기본 검사를 통과한 것입니다. 나중에 다시 확인하려면 압축을 푼 폴더에서 `bash doctor.sh`를 실행합니다. 서버 시작은 실제 접속 시 Remote-SSH가 관리합니다.

## 3. 오프라인 접속 PC에서 VS Code 설치

접속 PC용 ZIP을 풀고 그 폴더에서 실행합니다. Windows에서는 압축 해제 경로가 짧은 사용자 폴더를 사용하세요.

```powershell
powershell.exe -NoProfile -File .\install.ps1
```

```bash
bash install-client.sh
```

스크립트가 압축을 푼 폴더에 이 버전 전용 VS Code와 설정 폴더를 준비하고, 동봉한 VSIX를 설치합니다. 기존 VS Code 설치와 별도의 프로필입니다. 스크립트가 출력한 실행 파일을 열어 **Remote-SSH: Connect to Host…**로 접속합니다. 접속 전에 로컬 `ssh` 명령으로 같은 계정에 접속할 수 있어야 합니다.

기본 사용자 설정은 `"remote.SSH.useExecServer": false`입니다. Remote-SSH 0.128.0은 이 설정에서 `~/.vscode-server/bin/<커밋>/bin/code-server`를 찾아 실행합니다. `Output → Remote - SSH`에서 `Using commit id`와 `Found existing installation`을 확인하세요. 다른 서버 설치 위치를 쓰는 `remote.SSH.serverInstallPath` 설정이 있다면 이 번들의 경로와 맞춰야 합니다.

Windows에서 PowerShell 스크립트를 사용할 수 없다면, 공식 VS Code ZIP을 풀고 `Code.exe` 옆에 `data/user-data/User/` 폴더를 만들어 동봉한 `settings.json`을 넣습니다. VS Code를 실행한 후 **Extensions: Install from VSIX…**에서 `extensions.txt`의 순서대로 설치할 수 있습니다.

## 4. 양쪽이 오프라인인 상태에서 확인

SSH로 연결한 창에서 CentOS의 폴더를 열고, 테스트 파일을 저장하고 검색한 뒤 `Terminal → New Terminal`에서 서버 명령을 실행하세요. `doctor.sh`가 성공해도 실제 Remote-SSH 접속까지 확인해야 합니다. Codex 같은 추가 확장은 자체 실행 파일과 런타임 요구사항을 따로 확인합니다.

CentOS 7.4.1708 가상 머신의 `3.10.0-693.el7.x86_64` 커널과 시스템 glibc 2.17에서 서버를 검증했습니다. 외부 인터넷 경로와 시스템 Node가 없는 상태에서 일반 사용자 설치와 재설치, Node 24.22.1, ripgrep, PTY, VS Code Server 기동과 `/version` 응답을 확인했습니다. 회사 서버와 오프라인 데스크톱 사이의 Remote-SSH 연결은 현장에서 확인해야 합니다.

### 재접속할 때 `StatusCheckFailed`가 나오는 경우

`Output → Remote - SSH`에 `Checking server status on port … with wget` 직후 `wget: unrecognized option '--no-config'`가 나오면, 구형 CentOS `wget`이 Remote-SSH의 상태 검사 옵션을 거부한 것입니다. 이 검사는 이미 떠 있는 VS Code Server를 재사용할 때 실행되므로 첫 접속은 성공할 수 있습니다. [Microsoft Remote-SSH 이슈](https://github.com/microsoft/vscode-remote-release/issues/11244)

새 번들에는 아래 설정이 포함됩니다. 기존 설치에서는 접속 PC의 **Preferences: Open User Settings (JSON)** 에 아래 항목을 추가한 뒤 **Developer: Reload Window**를 실행하고 다시 접속하세요. 포터블 번들에서는 `Code.exe`가 있는 폴더의 `data/user-data/User/settings.json`을 직접 편집할 수도 있습니다. 기존 설정을 유지하려면 해당 키만 추가하거나 수정하면 됩니다.

```json
"remote.SSH.useCurlAndWgetConfigurationFiles": true
```

이 설정은 Remote-SSH가 원격 `wget`·`curl`의 설정 파일을 읽도록 허용합니다. 기존 서버를 검사하는 요청은 CentOS의 루프백 주소로 보내며 프록시를 사용하지 않습니다. 다른 오류가 표시되면 상태 검사 줄 직후의 오류를 확인하세요.

## 버전 업데이트와 이전 릴리스

`bundle-lock.json`에서 데스크톱과 서버를 **같은 Stable 커밋**으로 함께 갱신합니다. [Microsoft 업데이트 서비스](https://update.code.visualstudio.com/api/versions/1.146.0/server-linux-x64/stable)의 SHA-256, [서버의 Node 빌드 설정](https://github.com/microsoft/vscode/blob/1.146.0/remote/package.json), [Remote-SSH Marketplace 배포](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh)의 VSIX를 기준으로 고정합니다. 전용 런타임을 바꿀 때는 출처와 체크섬을 같은 파일에 기록합니다. 다시 생성한 두 파일을 실제 오프라인 환경과 커널 3.10에서 검증하세요.

이전 `tode`/Ghostty 구성은 [v0.1.0-wsl-test 태그의 설명서](https://github.com/hoony3000/terminal-code-centos74-offline/blob/v0.1.0-wsl-test/README-KO.txt)와 [기존 Release](https://github.com/hoony3000/terminal-code-centos74-offline/releases/tag/v0.1.0-wsl-test)에서 찾을 수 있습니다.
