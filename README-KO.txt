terminal-code CentOS 7.4 오프라인 시험 묶음
작성일: 2026-10-21 / x86_64 전용

1. 구성과 검증 범위

Windows PC의 최신 Linux WSL에서 화면을 그리고, SSH로 접속한 CentOS 7.4에서는
편집 서버만 실행합니다. CentOS에 Electron, GTK, X 서버는 필요하지 않습니다.

CentOS 설치는 일반 사용자 권한으로만 진행합니다. glibc 2.31과 C++ 런타임을
프로그램 폴더 안에 넣고 해당 실행 파일의 로더 경로에만 적용합니다.
/lib64, /usr/lib64, ldconfig, 시스템 패키지와 전역 LD_LIBRARY_PATH는 변경하지 않습니다.
프로젝트에서 실행하는 /bin/bash 등은 원래 시스템 라이브러리를 사용합니다.

검증 환경:
- 서버: WSL CentOS Linux 7.4.1708, glibc 2.17, 일반 사용자 uid 1000
- 클라이언트: WSL Ubuntu 24.04.3, WSLg, Ghostty 1.3.1
- 커널: WSL2 6.18.54.1-microsoft-standard-WSL2
- terminal-code: c6b14ebeddf2c902138c301abc84f19ac52e20e9
- Pixel npm: 0.0.23, patched Electron 44.2.0
- code-server: 4.132.0 / Code 1.132.0 / 포함된 Node 24.18.0
- patchelf: 0.15.0 (다른 버전으로 교체하지 마세요)

중요한 한계:
WSL 시험은 회사의 기본 3.10 커널을 검증한 것이 아닙니다. Node 24의 공식 x64
지원 조건은 kernel 4.18 이상입니다. 회사에서 uname -r과 doctor.sh 결과를
확인하기 전에는 실제 회사 장비에서의 동작이 확정되지 않습니다.
https://github.com/nodejs/node/blob/v24.18.0/BUILDING.md

Windows PC에는 WSLg가 동작하는 Ubuntu 24.04와 Kitty 그래픽 지원 터미널이
필요합니다. 이번 묶음에는 WSL 배포판과 Ghostty 자체는 포함하지 않았습니다.
기존 Windows Terminal/일반 SSH 창만으로 동일한 그래픽 화면을 보장하지 않습니다.
회사 PC에서 WSLg/Ghostty를 사용할 수 있는지는 별도 조건입니다.

2. 파일

terminal-code-centos74-remote.tar.gz : CentOS 쪽 설치 파일
terminal-code-linux-client.tar.gz   : 최신 Linux WSL 쪽 화면 클라이언트
corresponding-sources.tar.gz        : 라이브러리 대응 소스, 원본 저장소, 수정 패치
SHA256SUMS                         : 개별 파일 무결성 확인
TEST-RESULTS.txt                   : 검사 결과와 한계
install-client.sh                 : WSL 쪽 클라이언트 설치
Start-TerminalCode.ps1             : Windows에서 WSL의 시험용 터미널 실행

3. CentOS에 설치

회사 PC에서 원격 설치 파일만 CentOS의 사용자 작업 폴더로 복사합니다.
CentOS에서:

  sha256sum terminal-code-centos74-remote.tar.gz
  tar -xzf terminal-code-centos74-remote.tar.gz
  bash remote/install.sh
  "$HOME/.local/lib/tode-centos74/doctor.sh"

출력 마지막에 DOCTOR_OK가 표시되어야 합니다.
기본 위치는 $HOME/.local/lib/tode-centos74이고,
$HOME/.local/bin/tode 심볼릭 링크도 생성합니다.
기존 위치나 기존 tode 명령이 있으면 덮어쓰지 않고 중단합니다.

별도 위치로 설치하려면 절대 경로를 지정합니다. 이 경우 심볼릭 링크는 생성하지
않습니다. 설치 경로에는 공백, 콜론, 줄바꿈을 사용하지 마세요.

  bash remote/install.sh "$HOME/tools/tode-centos74"

이 경우 로컬 WSL에서 TODE_REMOTE_BIN에 회사 서버의 실제 절대 경로를 지정합니다.
설치 후 폴더를 통째로 이동하면 로더 경로가 맞지 않으므로, 새 위치에 원본 설치
파일을 다시 풀고 install.sh를 실행하세요.

4. Windows/WSL 클라이언트 설치

Ubuntu 24.04 WSL 안에서 Ghostty가 이미 실행되는지 먼저 확인합니다.
ZIP을 풀어둔 Windows 폴더로 WSL에서 이동한 다음:

  bash install-client.sh

회사 서버 SSH 접속은 WSL의 ssh 명령으로 먼저 확인합니다.
필요하면 WSL의 ~/.ssh/config에 회사 호스트, 포트, 사용자, 키를 설정하세요.
이 묶음에는 SSH 키, 계정 암호, 회사 설정은 들어 있지 않습니다.

  ssh user@company-host

Windows PowerShell에서 ZIP을 푼 폴더의 스크립트를 실행합니다.

  .\Start-TerminalCode.ps1 -Target user@company-host -Project /absolute/project/path

WSL 안에서 직접 실행할 수도 있습니다.

  "$HOME/.local/lib/tode-client/bin/open-ghostty" --ssh user@company-host /absolute/project/path

서버를 별도 위치에 설치한 경우:

  TODE_REMOTE_BIN=/home/yourname/tools/tode-centos74/bin/tode \
    "$HOME/.local/lib/tode-client/bin/open-ghostty" --ssh user@company-host /absolute/project/path

클라이언트와 서버의 버전이 다르거나 서버에 설치가 없으면 명확한 오류와 함께
중단합니다. SSH 시작 경로의 온라인 설치 코드는 제거했습니다.
인터넷에서 자동으로 실행 파일을 받지 않습니다.

5. 사용과 종료

VS Code 화면의 파일 탐색기에서 파일을 열고 Ctrl+S로 저장합니다.
내장 터미널은 메뉴의 Terminal > New Terminal로 열 수 있습니다.
전용 실행기는 Ghostty 사용자 설정을 수정하지 않고 별도 설정 파일을 사용합니다.
터미널 자체의 기본 단축키를 비워 VS Code와의 충돌을 줄였습니다.
클립보드 접근 확인 창이 뜨면 이번에 사용할 내용인지 확인하고 처리하세요.

원격 서버 종료:

  "$HOME/.local/bin/tode" --shutdown

서버는 127.0.0.1에서만 듣고, 암호 인증과 일회성 접속 티켓을 사용합니다.
방화벽 포트를 열지 않습니다. 기존 SSH 연결이 통신을 운반합니다.
이 구성은 추가적인 파일/명령 실행 격리 장치가 아닙니다. 내장 셸은 로그인한
사용자의 권한으로 실행됩니다.

6. 오프라인 확장 기능

기본 편집 기능은 포함되어 있지만 언어 서버, 디버거, VSIX 확장은 별도입니다.
필요한 확장은 외부에서 VSIX를 받아 회사 반입 절차에 따라 옮긴 다음 설치합니다.

  "$HOME/.local/bin/tode" --install-extension /absolute/path/extension.vsix

확장 기능 자체가 추가 파일을 다운로드하는지는 확장별로 확인해야 합니다.

7. 진단과 제거

doctor.sh 출력을 확인하세요. 커널 버전, Node, 네이티브 터미널 모듈을 검사합니다.
로그와 사용자 상태는 설치 폴더의 var/ 아래에 있습니다.
로그나 server.json에는 접속 정보가 있으므로 GitHub에 올리지 마세요.

원격 설치를 제거하려면 먼저 --shutdown으로 서버를 종료한 뒤, 실제 설치 경로와
사용자 bin 심볼릭 링크를 확인하고 삭제합니다. 시스템 라이브러리를 되돌릴 작업은
없습니다. 원본 압축파일은 다시 설치할 때 사용할 수 있습니다.

8. 출처

https://github.com/zenbu-labs/terminal-code
https://github.com/zenbu-labs/terminal-browser/tree/main/pixel
https://github.com/coder/code-server/releases/tag/v4.132.0
https://github.com/NixOS/patchelf/releases/tag/0.15.0
https://archive.ubuntu.com/ubuntu/

라이선스 및 대응 소스는 원격 파일의 licenses/와 corresponding-sources.tar.gz에
동봉했습니다. 체크섬은 전송 손상을 확인하며 출처의 전자서명을 대신하지 않습니다.
