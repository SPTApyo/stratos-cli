#!/bin/bash

# STRATOS | PACKAGING HELPER
# Generates system package definitions (AUR, RPM) and prepares PyPI dist

BLUE='\033[0;34m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

# Work from project root
cd "$(dirname "$0")/../.."

# Dynamic Metadata Extraction (Source of Truth: stratos/__init__.py)
VERSION=$(grep "__version__" stratos/__init__.py | cut -d '"' -f 2)
APP_NAME=$(grep "__app_name__" stratos/__init__.py | cut -d '"' -f 2)
DESC=$(grep "__description__" stratos/__init__.py | cut -d '"' -f 2)
URL=$(grep "__url__" stratos/__init__.py | cut -d '"' -f 2)
AUTHOR=$(grep "__author__" stratos/__init__.py | cut -d '"' -f 2)
EMAIL=$(grep "__author_email__" stratos/__init__.py | cut -d '"' -f 2)
LICENSE=$(grep "__license__" stratos/__init__.py | cut -d '"' -f 2)

echo -e "${BLUE}${BOLD}› ${APP_NAME} PACKAGER v${VERSION}${NC}"

# 1. Prepare PyPI Distribution
echo -e "\n${CYAN}[1/3] Building Python Source Distribution...${NC}"
rm -rf dist/ build/ *.egg-info
python3 -m build --sdist --wheel > /dev/null
echo -e "${GREEN}✓ Dist files created in /dist${NC}"

# 2. Generate Arch Linux PKGBUILD (AUR)
echo -e "\n${CYAN}[2/3] Generating AUR PKGBUILD...${NC}"
cat <<EOF > PKGBUILD
# Maintainer: ${AUTHOR} <${EMAIL}>
pkgname=${APP_NAME}
pkgver=${VERSION}
pkgrel=1
pkgdesc="${DESC}"
arch=('any')
url="${URL}"
license=('${LICENSE}')
depends=('python>=3.10' 'python-rich' 'python-dotenv' 'python-readchar' 'python-google-generativeai' 'python-duckduckgo-search')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=("${URL}/archive/refs/tags/v\${pkgver}.tar.gz")
sha256sums=('SKIP')

build() {
    cd "stratos-cli-\${pkgver}"
    python -m build --wheel --no-isolation
}

package() {
    cd "stratos-cli-\${pkgver}"
    python -m installer --destdir="\${pkgdir}" dist/*.whl
}
EOF
echo -e "${GREEN}✓ PKGBUILD generated.${NC}"

# 3. Generate Fedora RPM Spec
echo -e "\n${CYAN}[3/3] Generating Fedora RPM Spec...${NC}"
cat <<EOF > stratos.spec
Name:           ${APP_NAME}
Version:        ${VERSION}
Release:        1%{?dist}
Summary:        ${DESC}

License:        ${LICENSE}
URL:            ${URL}
Source0:        ${URL}/archive/refs/tags/v%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

%description
${DESC}

%prep
%autosetup -n stratos-cli-%{version}

%build
%py3_build

%install
%py3_install

%files
%{_bindir}/stratos
%{python3_sitelib}/stratos*

%changelog
* $(date +"%a %b %d %Y") ${AUTHOR} <${EMAIL}> - ${VERSION}-1
- Initial release
EOF
echo -e "${GREEN}✓ stratos.spec generated.${NC}"

# 4. Instructions
echo -e "\n${YELLOW}${BOLD}NEXT STEPS:${NC}"
echo -e "1. ${BOLD}PyPI (Global):${NC} Run 'twine upload dist/*' to publish."
echo -e "2. ${BOLD}Arch (AUR):${NC}    Copy 'PKGBUILD' to your AUR repo."
echo -e "3. ${BOLD}Fedora (COPR):${NC} Use 'stratos.spec' for COPR build."
echo -e "\n${BLUE}Happy Packaging!${NC}"
