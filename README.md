# terminal-code CentOS 7.4 오프라인 시험 묶음

Windows의 최신 Linux WSL에서 terminal-code 화면을 그리고, SSH로 연결한 CentOS 7.4에서 편집 서버를 실행하는 사용자 권한 설치 묶음입니다.

**WSL CentOS 7.4에서 SSH 화면 표시, 파일 편집·저장, 내장 터미널, 외부 네트워크가 없는 상태의 서버 기동을 검증했습니다. 회사의 3.10 커널에서는 아직 검증하지 않았습니다.** 포함된 Node 24의 공식 GNU/Linux x64 지원 기준은 커널 4.18 이상입니다.

## 다운로드

[설치 ZIP과 체크섬 받기](https://github.com/hoony3000/terminal-code-centos74-offline/releases/tag/v0.1.0-wsl-test)

ZIP 안에 원격 설치 파일, WSL 화면 클라이언트, 설치 스크립트, 한국어 설명서, 체크섬, 대응 소스가 들어 있습니다. 큰 바이너리는 Releases에만 보관합니다.

## 회사 CentOS에서

ZIP에서 원격 설치 파일을 꺼내 사용자 작업 폴더로 옮긴 후 실행합니다.

```sh
tar -xzf terminal-code-centos74-remote.tar.gz
bash remote/install.sh
"$HOME/.local/lib/tode-centos74/doctor.sh"
```

기본 설치 위치는 `~/.local/lib/tode-centos74`이며 `~/.local/bin/tode` 링크를 만듭니다. 기존 설치나 명령은 덮어쓰지 않습니다. `sudo`가 필요하지 않습니다. `/lib64`와 `/usr/lib64`, 시스템 패키지, `ldconfig`, 전역 `LD_LIBRARY_PATH`를 변경하지 않습니다.

전용 glibc 2.31과 C++ 런타임은 설치 폴더 안에 들어 있습니다. ELF 실행 파일에만 전용 로더와 RPATH를 적용하며 공유 모듈은 원본을 유지합니다. 내장 터미널의 `/bin/bash`는 시스템의 glibc 2.17을 사용합니다.

## Windows/WSL에서

**기존 WSLg + Ubuntu 24.04 + Ghostty가 필요합니다. WSL 배포판과 Ghostty 자체는 이 묶음에 포함되어 있지 않습니다.** 회사 Windows PC에서 이 조건을 사용할 수 있는지 확인해야 합니다.

ZIP을 푼 폴더에서 WSL로 `install-client.sh`를 실행한 다음, WSL의 `ssh user@host`가 정상 작동하는지 확인합니다.

```sh
bash install-client.sh
"$HOME/.local/lib/tode-client/bin/open-ghostty" --ssh user@host /absolute/project/path
```

PowerShell 실행기도 제공합니다.

```powershell
.\Start-TerminalCode.ps1 -Target user@host -Project /absolute/project/path
```

SSH 준비 단계의 온라인 자동 설치 코드는 제거했습니다. 서버 버전이 다르면 중단합니다. 서버는 루프백에서만 듣고 인증을 사용하며 기존 SSH 연결로 통신합니다. 새 방화벽 포트를 열지 않습니다.

## 검증과 한계

- 서버: CentOS 7.4.1708, glibc 2.17, uid 1000, WSL2 커널 6.18.54.1.
- 화면: WSL Ubuntu 24.04.3, WSLg, Ghostty 1.3.1.
- 최종 설치 압축파일을 새 경로에 풀어 SSH 연결, 파일 저장, 내장 셸의 `TERMINAL_OK` 파일 생성을 확인했습니다.
- 외부 인터페이스와 라우트가 없는 rootless 네트워크 네임스페이스에서 인증 후 workbench HTTP 200을 확인했습니다.
- 시스템 libc 및 libstdc++ 체크섬은 설치·사용 전후 동일했습니다.
- 회사의 커널, SSH 정책, 한글 IME, 확장별 다운로드, 대규모 프로젝트 성능과 장기 안정성은 검증 범위 밖입니다.

[전체 설치 설명](README-KO.txt) · [검사 결과](TEST-RESULTS.txt) · [배포 manifest](MANIFEST.json)

## 고정 버전과 출처

- [terminal-code](https://github.com/zenbu-labs/terminal-code): `c6b14ebeddf2c902138c301abc84f19ac52e20e9`
- [Pixel](https://github.com/zenbu-labs/terminal-browser/tree/pixel-v0.0.23/pixel): npm `0.0.23`, 소스 `fd5f1798b128cd71508aa534ddbf67caf05ec0b8`
- [code-server](https://github.com/coder/code-server/releases/tag/v4.132.0): `4.132.0`, Code `1.132.0`, Node `24.18.0`
- patched Electron `44.2.0`, patchelf `0.15.0`, Ubuntu glibc `2.31-0ubuntu9.18`

원본 라이선스와 라이브러리 대응 소스는 설치 ZIP에 동봉했습니다. 이 저장소는 위 프로젝트들의 공식 CentOS 지원 배포판이 아닌 시험용 패키징입니다.
