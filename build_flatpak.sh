#!/bin/bash
set -e

# Add flathub remote if not exists (user)
flatpak remote-add --if-not-exists --user flathub https://flathub.org/repo/flathub.flatpakrepo

# Install runtime and sdk
echo "Installing/Updating Runtime and SDK..."
flatpak install -y --user flathub org.kde.Platform//6.6 org.kde.Sdk//6.6

# Build
echo "Building..."
flatpak-builder --user --force-clean build-dir org.loofi.FedoraTweaks.yml

# Create repo
echo "Exporting to repo..."
flatpak build-export repo build-dir

# Create bundle
echo "Creating bundle..."
flatpak build-bundle repo loofi-fedora-tweaks.flatpak org.loofi.FedoraTweaks

echo "Flatpak bundle created: loofi-fedora-tweaks.flatpak"
