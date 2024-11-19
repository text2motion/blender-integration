# Blender Integration

> [!NOTE]
> This package is currently in early preview and is subject to changes at any time.

![Example animation generation](images/generate_animation_example.gif)

Text2Motion's Blender integration client, can be use to make request to Text2Motion's API for generating Animation on a given Mixamo model.

Currently, the animation can only be generated for character with Mixamo rig name and structure. Also only model imported as GLB are supported, FBX currently does not work. This repo contains an example Mixamo model in GLB that can be downloaded and imported to Blender to test out the package. Support for retargeting to other humanoid rig structure may be introduced in the future.

## Table of Contents

1. [Getting Started](#getting-started)
   1. [Obtaining the API Key](#obtaining-the-api-key)
   2. [Blender installation](#blender-installation)
   3. [Installing the extension](#installing-the-extension)
   4. [Animation Generation](#animation-generation)
2. [Development](#development)
   1. [Building the extension](#building-the-extension)
3. [Features](#features)
   1. [Apply Root Motion](#apply-root-motion)

## Getting Started

### Obtaining the API Key

In order to use Text2Motion, you must sign up for an account and obtain the API Key via the developer portal.

1. Go to [https://developer.text2motion.ai/](https://developer.text2motion.ai/)  
![Developer Portal](images/Obtaining_API_Key-Portal.png)
2. Click on Sign in on the upper right corner  
![Sign in](images/Obtaining_API_Key-Sign_In.png)
3. Click on **LOGIN WITH SAML**
4. Choose either **Continue with Google** for Google SSO, or **Sign Up** with any email you own
5. Click on your username on the upper right corner of the site
6. Click on **Apps**  
![Apps](images/Obtaining_API_Key-Apps.png)
7. Click on **+ NEW APP** on the right side of the screen  
![New App](images/Obtaining_API_Key-New_App.png)
8. Put in an **App Name**, it could be `Blender Client` or whatever you want
9. Click **Enable** for **Text2motion Free Tier**  
![Create App](images/Obtaining_API_Key-Create_App.png)
10. Click **Save**
11. You should now have an API Key. This will be needed later  
![Api Key](images/Obtaining_API_Key-Key.png)

### Blender installation

The minimum supported Blender version is `4.2.0`. This package was only tested for Blender version `4.2.3`. Other version have not been tested.

### Installing the extension

1. Download the extension from the [Releases](https://github.com/text2motion/blender-integration/releases) page.
2. Go to **Edit > Preferences...**  
![Preference drop down](images/Installing-Preference.png)
3. Go to **Extensions**, click on the down arrow on the right and Select **Install from Disk**  
![Install from disk](images/Installing-Install_from_Disk.png)
4. Select the downloaded extension zip file and click **Install from Disk**
5. After that, the extension should be installed  
![Installed](images/Installing-Done.png)

### Animation Generation

> [!NOTE]
> All generated animations are licensed under [CC-by-4.0](https://creativecommons.org/licenses/by/4.0/)

This instruction uses an example Mixamo Rig provided in the repository. You may try using your own model as long as it is using Mixamo Rig.

1. Download [Y Bot.glb](https://github.com/text2motion/blender-integration/raw/refs/tags/releases/0.1.0/assets/Y%20Bot.glb?download=)
2. In Blender, go to **File > Import > glTF 2.0 (.glb/gltf)**  
![Import GLB file](images/Animation_Generation-Import_GLB.png)
3. Select the downloaded `Y Bot.glb` and click **Import glTF 2.0**
4. Go to the **Animation** workspace
5. In the **3D View port**, locate the left arrow on the upper right corner of the screen, expand it and select the **Animation** tab  
![Animation tab](images/Animation_Generation-Animation_tab.gif)
6. Fill in the key you obtained from [Obtaining the API Key](#obtaining-the-api-key) here  
![Save API Key](images/Animation_Generation-Save_API_Key.png)
7. After that, you should be able to generate animation by providing a prompt  
![Generate](images/Animation_Generation-Generate.png)

## Development

We recommend using Visual Studio Code for developing this package. This package comes with a devcontainer with Blender installed and uses the [Blender Developer](https://marketplace.visualstudio.com/items?itemName=JacquesLucke.blender-development) Visual Studio Code extension.

To get started:

1. Install [Visual Studio Code](https://code.visualstudio.com/)
2. Install [Dev Container extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
3. Press `Ctrl+shift+P` and select `Dev Containers: Reopen in Container`
4. From here, you can launch Blender with the extension installed by pressing `Ctrl+shift+P` and select `Blender: Build and Start`. To reload the changes, select `Blender: Reload Addons`

### Troubleshooting

#### Blender crashes on Preferences > add-on

Sometimes Blender would get in a state such that it crashes when you open Preferences > Add-on or Extension. To recover from that issue, comment out `wheels` in `blender_manifest.tom.template`, start Blender, open Preference and attempt to install Text2Motion. From here you should get an error saying the dependencies are missing, but it won't crash. After that, you can uncomment `wheels` and it should go back to normal again.

### Building the extension

To build the extension, press `Ctrl+shift+P`, select `Tasks: Run Task` then select `Build Extension`. The resulting extension will be located under `build/` at the root of the package.

## Features

### Apply Root Motion

By default, Text2Motion apply root motion to the generated animation. This means the resulting animation can leave the initial position. If you want to disable root motion and have the model animated in place, you can uncheck **Apply Root Motion** under **Advanced Options**  
![Apply Root Motion](images/Features_apply-root-motion.gif)

Note that with **Apply Root Motion** unchecked, there will be no keyframe for the root bone. If the initial position of the model is away from the origin when the animation is generated, it will render from where the last position was instead of from the origin. You can t-pose the model to move it back to the origin by pressing `A`, `alt+G`, `alt+R`, `alt+S`.
