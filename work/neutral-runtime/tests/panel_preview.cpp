// Render the real native panel to PNG using a separate software D3D11 device.
// No window, process attachment, game renderer, or game files are involved.
#include "slider_panel.h"
#include "presets.h"
#include <Windows.h>
#include <d3d11.h>
#include <wincodec.h>
#include <wrl/client.h>
#include <backends/imgui_impl_dx11.h>
#include <cstdio>
#include <stdexcept>
using Microsoft::WRL::ComPtr;
using namespace neutral;
static void checked(HRESULT hr) {if (FAILED(hr)) throw std::runtime_error("Software panel rendering failed (HRESULT "+std::to_string(static_cast<unsigned>(hr))+")");}
int wmain(int argc,wchar_t** argv) {try {
    if (argc<2) throw std::runtime_error("Usage: neutral_panel_preview <output.png> [preset.json]");
    checked(CoInitializeEx(nullptr,COINIT_MULTITHREADED));
    FitMesh m;m.base={{0,0,0},{0,0,-.1}};m.seam_normals.assign(2,{0,1,0});
    for (auto& f:m.fields) f.assign(2,0);
    const auto p=argc>2?load_preset(argv[2]):default_parameters();
    ControlSession session(std::make_shared<const Fitter>(std::move(m)),p);
    session.wait_for_staged(1,std::chrono::seconds(2));
    ComPtr<ID3D11Device> device;ComPtr<ID3D11DeviceContext> context;
    checked(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context));
    constexpr unsigned width=800,height=960;
    D3D11_TEXTURE2D_DESC desc{};desc.Width=width;desc.Height=height;desc.MipLevels=1;desc.ArraySize=1;
    desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;desc.SampleDesc.Count=1;desc.Usage=D3D11_USAGE_DEFAULT;desc.BindFlags=D3D11_BIND_RENDER_TARGET;
    ComPtr<ID3D11Texture2D> image;checked(device->CreateTexture2D(&desc,nullptr,&image));
    ComPtr<ID3D11RenderTargetView> target;checked(device->CreateRenderTargetView(image.Get(),nullptr,&target));
    ImGui::CreateContext();auto& io=ImGui::GetIO();io.IniFilename=nullptr;io.DisplaySize={float(width),float(height)};io.DeltaTime=1.f/60;
    wchar_t windows[MAX_PATH]{};GetWindowsDirectoryW(windows,MAX_PATH);
    const auto font_path=std::filesystem::path(windows)/"Fonts/segoeui.ttf";
    if (!std::filesystem::is_regular_file(font_path) || !io.Fonts->AddFontFromFileTTF(font_path.string().c_str(),17)) {
        ImFontConfig font{};font.SizePixels=17;io.Fonts->AddFontDefault(&font);
    }
    ImGui::StyleColorsDark();auto& style=ImGui::GetStyle();style.WindowRounding=8;style.FrameRounding=4;style.ItemSpacing={10,8};style.WindowPadding={20,18};
    style.Colors[ImGuiCol_WindowBg]={.075f,.085f,.105f,1};style.Colors[ImGuiCol_FrameBg]={.14f,.17f,.21f,1};
    style.Colors[ImGuiCol_SliderGrab]={.54f,.72f,.65f,1};style.Colors[ImGuiCol_Button]={.19f,.31f,.29f,1};
    if (!ImGui_ImplDX11_Init(device.Get(),context.Get())) throw std::runtime_error("Cannot initialize preview renderer.");
    SliderPanel panel;
    for (int frame=0;frame<3;++frame) {
        ImGui_ImplDX11_NewFrame();ImGui::NewFrame();ImGui::SetNextWindowPos({24,24},ImGuiCond_Always);ImGui::SetNextWindowSize({752,912},ImGuiCond_Always);
        panel.draw(session);ImGui::Render();const float background[]{.035f,.04f,.05f,1};
        auto* view=target.Get();context->OMSetRenderTargets(1,&view,nullptr);context->ClearRenderTargetView(view,background);
        ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());
    }
    desc.Usage=D3D11_USAGE_STAGING;desc.BindFlags=0;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> staging;checked(device->CreateTexture2D(&desc,nullptr,&staging));context->CopyResource(staging.Get(),image.Get());
    D3D11_MAPPED_SUBRESOURCE mapped{};checked(context->Map(staging.Get(),0,D3D11_MAP_READ,0,&mapped));
    ComPtr<IWICImagingFactory> factory;checked(CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&factory)));
    ComPtr<IWICStream> stream;checked(factory->CreateStream(&stream));checked(stream->InitializeFromFilename(argv[1],GENERIC_WRITE));
    ComPtr<IWICBitmapEncoder> encoder;checked(factory->CreateEncoder(GUID_ContainerFormatPng,nullptr,&encoder));checked(encoder->Initialize(stream.Get(),WICBitmapEncoderNoCache));
    ComPtr<IWICBitmapFrameEncode> frame;checked(encoder->CreateNewFrame(&frame,nullptr));checked(frame->Initialize(nullptr));checked(frame->SetSize(width,height));
    WICPixelFormatGUID format=GUID_WICPixelFormat32bppBGRA;checked(frame->SetPixelFormat(&format));
    if (!IsEqualGUID(format,GUID_WICPixelFormat32bppBGRA)) throw std::runtime_error("Unsupported PNG pixel format.");
    std::vector<BYTE> bgra(width*height*4);
    for (unsigned y=0;y<height;++y) for (unsigned x=0;x<width;++x) {
        const auto* pixel=static_cast<const BYTE*>(mapped.pData)+y*mapped.RowPitch+x*4;
        auto* dest=bgra.data()+(y*width+x)*4;dest[0]=pixel[2];dest[1]=pixel[1];dest[2]=pixel[0];dest[3]=pixel[3];
    }
    checked(frame->WritePixels(height,width*4,static_cast<UINT>(bgra.size()),bgra.data()));checked(frame->Commit());checked(encoder->Commit());
    context->Unmap(staging.Get(),0);ImGui_ImplDX11_Shutdown();ImGui::DestroyContext();
    std::puts("Rendered native panel offline with software D3D11.");return 0;
}catch(const std::exception& e) {std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}}
