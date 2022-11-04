#include <QMouseEvent>
#include <QGuiApplication>

#include "NGLScene.h"
#include <ngl/NGLInit.h>
#include <ngl/NGLStream.h>
#include <ngl/Transformation.h>
#include <ngl/VAOPrimitives.h>
#include <ngl/ShaderLib.h>

NGLScene::NGLScene()
{
  setTitle("ngl::NCCAPointBake demo");
  m_active=true;
}


NGLScene::~NGLScene()
{
  std::cout<<"Shutting down NGL, removing VAO's and Shaders\n";
}

void NGLScene::resizeGL( int _w, int _h )
{
  m_project=ngl::perspective( 45.0f, static_cast<float>( _w ) / _h, 0.05f, 350.0f );
  m_win.width  = static_cast<int>( _w * devicePixelRatio() );
  m_win.height = static_cast<int>( _h * devicePixelRatio() );
}

void NGLScene::initializeGL()
{
  // we must call this first before any other GL commands to load and link the
  // gl commands from the lib, if this is not done program will crash
  ngl::NGLInit::initialize();

  glClearColor(0.4f, 0.4f, 0.4f, 1.0f);			   // Grey Background
  // enable depth testing for drawing
  glEnable(GL_DEPTH_TEST);
  // enable multisampling for smoother drawing
  glEnable(GL_MULTISAMPLE);
  // Now we will create a basic Camera from the graphics library
  // This is a static camera so it only needs to be set once
  // First create Values for the camera position
  ngl::Vec3 from(0,0,30);
  ngl::Vec3 to(0,0,0);
  ngl::Vec3 up(0,1,0);

  m_view=ngl::lookAt(from,to,up);
  m_project=ngl::perspective(45,720.0f/576.0f,0.5f,320.0f);
  // we are creating a shader called Phong
  ngl::ShaderLib::createShaderProgram("Phong");
  // now we are going to create empty shaders for Frag and Vert
  ngl::ShaderLib::attachShader("PhongVertex",ngl::ShaderType::VERTEX);
  ngl::ShaderLib::attachShader("PhongFragment",ngl::ShaderType::FRAGMENT);
  // attach the source
  ngl::ShaderLib::loadShaderSource("PhongVertex","shaders/PhongVertex.glsl");
  ngl::ShaderLib::loadShaderSource("PhongFragment","shaders/PhongFragment.glsl");
  // compile the shaders
  ngl::ShaderLib::compileShader("PhongVertex");
  ngl::ShaderLib::compileShader("PhongFragment");
  // add them to the program
  ngl::ShaderLib::attachShaderToProgram("Phong","PhongVertex");
  ngl::ShaderLib::attachShaderToProgram("Phong","PhongFragment");

  // now we have associated this data we can link the shader
  ngl::ShaderLib::linkProgramObject("Phong");
  // and make it active ready to load values
  ngl::ShaderLib::use("Phong");
  ngl::ShaderLib::setUniform("Normalize",0);
  ngl::Vec4 lightPos(20.0f,20.0f,-20.0f,1.0f);
  ngl::Mat4 iv=m_view;
  iv.inverse().transpose();
  ngl::ShaderLib::setUniform("light.position",lightPos*iv);
  ngl::ShaderLib::setUniform("light.ambient",0.1f,0.1f,0.1f,1.0f);
  ngl::ShaderLib::setUniform("light.diffuse",1.0f,1.0f,1.0f,1.0f);
  ngl::ShaderLib::setUniform("light.specular",0.8f,0.8f,0.8f,1.0f);
  // gold like phong material
  ngl::ShaderLib::setUniform("material.ambient",0.274725f,0.1995f,0.0745f,0.0f);
  ngl::ShaderLib::setUniform("material.diffuse",0.75164f,0.60648f,0.22648f,0.0f);
  ngl::ShaderLib::setUniform("material.specular",0.628281f,0.555802f,0.3666065f,0.0f);
  ngl::ShaderLib::setUniform("material.shininess",51.2f);
  ngl::ShaderLib::setUniform("viewerPos",from);
  glEnable(GL_DEPTH_TEST); // for removal of hidden surfaces
  // first we create a mesh from an obj passing in the obj file and textures
  m_mesh=std::make_unique< ngl::Obj>("models/Shark.obj");
  // now we need to create this as a VBO so we can draw it
  m_mesh->createVAO();
  std::cout<<"mesh verts"<<m_mesh->getNumVerts()<<"\n";
  m_animData = std::make_unique<  ngl::NCCAPointBake>("models/Shark.xml");
  m_animData->setFrame(0);
  m_animData->attachMesh(m_mesh.get());
  m_frame=0;
  // enable multi sampling
  glEnable(GL_MULTISAMPLE);
  m_animTimer=startTimer(8);
  glPolygonMode(GL_FRONT_AND_BACK,GL_LINE);
}


void NGLScene::loadMatricesToShader()
{
  ngl::ShaderLib::use("Phong");
  ngl::Mat4 MV;
  ngl::Mat4 MVP;
  ngl::Mat3 normalMatrix;
  ngl::Mat4 M;
  M=m_mouseGlobalTX;
  MV=m_view*M;
  MVP=m_project*MV ;
  normalMatrix=MV;
  normalMatrix.inverse().transpose();
  ngl::ShaderLib::setUniform("MV",MV);
  ngl::ShaderLib::setUniform("MVP",MVP);
  ngl::ShaderLib::setUniform("normalMatrix",normalMatrix);
  ngl::ShaderLib::setUniform("M",M);
}

void NGLScene::paintGL()
{
  // clear the screen and depth buffer
  glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
  glViewport(0,0,m_win.width,m_win.height);
  // Rotation based on the mouse position for our global transform
  auto rotX = ngl::Mat4::rotateX(m_win.spinXFace);
  auto rotY = ngl::Mat4::rotateY(m_win.spinYFace);
  // multiply the rotations
  m_mouseGlobalTX=rotY*rotX;
  // add the translations
  m_mouseGlobalTX.m_m[3][0] = m_modelPos.m_x;
  m_mouseGlobalTX.m_m[3][1] = m_modelPos.m_y;
  m_mouseGlobalTX.m_m[3][2] = m_modelPos.m_z;

        // draw the mesh
  loadMatricesToShader();
  m_mesh->draw();

}

//----------------------------------------------------------------------------------------------------------------------

void NGLScene::keyPressEvent(QKeyEvent *_event)
{
  // this method is called every time the main window recives a key event.
  // we then switch on the key value and set the camera in the GLWindow
  switch (_event->key())
  {
  // escape key to quite
  case Qt::Key_Escape : QGuiApplication::exit(EXIT_SUCCESS); break;
  // turn on wirframe rendering
  case Qt::Key_W : glPolygonMode(GL_FRONT_AND_BACK,GL_LINE); break;
  // turn off wire frame
  case Qt::Key_S : glPolygonMode(GL_FRONT_AND_BACK,GL_FILL); break;
  // show full screen
  case Qt::Key_F : showFullScreen(); break;
  // show windowed
  case Qt::Key_N : showNormal(); break;
  case Qt::Key_Space : m_active^=true; break;

  default : break;
  }
  // finally update the GLWindow and re-draw
  //if (isExposed())
    update();
}

void NGLScene::timerEvent(QTimerEvent * )
{
	if (m_active == false)
	{
		return;
	}
	if(++m_frame >m_animData->getNumFrames())
	{
		m_frame=0;
	}
	m_animData->setMeshToFrame(m_frame);
	update();
}
