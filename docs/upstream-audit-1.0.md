# Auditoria upstream final - 1.0

Data: 2026-10-22. Branch de trabalho: `port/kubuntu-26.04`.
Base: `d0f58a963b45e740976d46b60901ab97cd5ea430`, RC1 com CPU/CI/icones.
O checkout inicial estava limpo em master, no mesmo commit; foi trocado para
a branch portada antes de qualquer edicao. Master nao foi alterada.

## Evidencia

- `git fetch upstream`: concluido, sem merge.
- `git rev-parse upstream/master`:
  `5c8046c00daf1391260093de251a9fffa2e540d7`.
- `git log --oneline 5c8046c..upstream/master` e
  `git diff --stat 5c8046c..upstream/master`: vazios.
- `git ls-remote https://github.com/canonical/ubuntu-drivers-common.git HEAD`:
  `ffb948b95f7c85d5a92275a9aaa53b6d9e2e2453`.
- `dpkg-query -W ubuntu-drivers-common` e `apt-cache policy`:
  instalado/candidato `1:0.10.9`, resolute/main, prioridade 500.

Os hashes sao iguais aos da auditoria RC1. Nenhuma mudanca funcional de commits
upstream foi encontrada; nenhuma exige port ou bloqueia a promocao local 1.0.
O contrato efetivamente instalado continua prioritario sobre APIs do master UDC.

## Issues e classificacao

A lista aberta Mint foi consultada novamente pela API HTTPS oficial. Issues e
PR nao merged nao constituem mudanca funcional incorporada ao upstream.

| Item | Classificacao | Decisao |
| --- | --- | --- |
| #112 DisplayLink/EVDI | Nova classe de hardware | Fora do escopo; adiar. |
| #111 535/470/server | NVIDIA/recomendacao | Preservar autoridade UDC e testes server. |
| #110 falso offline | Bugfix GTK/rede | Nao aplicavel; Qt nao testa servidor especifico. |
| #109 PRIME/assinatura | NVIDIA/Secure Boot | Preservar preflight e MOK exata; hardware real limitado. |
| #107 WIP aviso Secure Boot | UI GTK/PR | Nao copiar PR nao merged. |
| #103 aviso Secure Boot | Secure Boot/UI | Estados semanticos e blockers ja existentes. |
| #100 enrollment | MOK | Manter somente leitura, sem enrollment proprio. |
| #99 versao NVIDIA | APT/recomendacao | Preservar candidate/pinning, nao escolher versao maxima. |
| #96 radeon/amdgpu | Nova politica de driver | Adiar; freeze da versao final. |

UI GTK/XApp, backend, NVIDIA, Broadcom, Secure Boot/MOK, packaging, traducoes e
bugfixes genericos: sem delta de commits a incorporar desde a ultima auditoria.
Nenhuma politica de driver, API PackageKit ou dependencia foi alterada pela
auditoria. Nenhuma operacao de driver, modulo, DKMS ou MOK foi executada.

Fontes primarias:
- https://github.com/linuxmint/mintdrivers/commit/5c8046c00daf1391260093de251a9fffa2e540d7
- https://github.com/canonical/ubuntu-drivers-common/commit/ffb948b95f7c85d5a92275a9aaa53b6d9e2e2453
- https://api.github.com/repos/linuxmint/mintdrivers/issues?state=open&per_page=100

Conclusao: nenhum bloqueador upstream conhecido para 1.0. Nao foi realizado
merge automatico, push, tag ou publicacao.
