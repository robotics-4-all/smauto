import uuid
import os
import base64
import subprocess
import shutil

import tarfile

from smauto.language import build_model
from fastapi import FastAPI, File, UploadFile, status, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from smauto.transformations import model_to_vnodes

api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMP_DIR = '/tmp/smauto'


if not os.path.exists(TMP_DIR):
    os.mkdir(TMP_DIR)


@api.get("/", response_class=HTMLResponse)
async def root():
    return """
<html>
<head>
<style>
html,body{
    margin:0;
    height:100%;
}
img{
  display:block;
  width:100%; height:100%;
  object-fit: cover;
}
</style>
</head>
<body>
 <img src="https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fnews.images.itv.com%2Fimage%2Ffile%2F492835%2Fimg.jpg&f=1&nofb=1" alt="">
</body>
</html>
    """


@api.post("/validate")
async def validate_file(file: UploadFile = File(...)):
    print(f'Validation for request: file=<{file.filename}>,' + \
          f' descriptor=<{file.file}>')
    resp = {
        'status': 200,
        'message': ''
    }
    fd = file.file
    u_id = uuid.uuid4().hex[0:8]
    fpath = os.path.join(
        TMP_DIR,
        f'model_for_validation-{u_id}.auto'
    )
    with open(fpath, 'w') as f:
        f.write(fd.read().decode('utf8'))
    try:
        model = build_model(fpath)
        print('Model validation success!!')
        resp['message'] = 'Model validation success'
    except Exception as e:
        print('Exception while validating model. Validation failed!!')
        print(e)
        resp['status'] = 404
        resp['message'] = str(e)
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")
    return resp


@api.post("/validate/b64")
async def validate_b64(text: str = ''):
    if len(text) == 0:
        return 404
    resp = {
        'status': 200,
        'message': ''
    }
    fdec = base64.b64decode(text)
    u_id = uuid.uuid4().hex[0:8]
    fpath = os.path.join(
        TMP_DIR,
        'model_for_validation-{}.auto'.format(u_id)
    )
    with open(fpath, 'wb') as f:
        f.write(fdec)
    try:
        model = build_model(fpath)
        print('Model validation success!!')
        resp['message'] = 'Model validation success'
    except Exception as e:
        print('Exception while validating model. Validation failed!!')
        print(e)
        resp['status'] = 404
        resp['message'] = str(e)
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")
    return resp


@api.post("/interpret")
async def interpret(model_file: UploadFile = File(...),
                    container: str = 'subprocess',
                    wait: bool = False):
    print(f'Interpret Request: file=<{model_file.filename}>,' + \
          f' descriptor=<{model_file.file}>')
    resp = {
        'status': 200,
        'message': ''
    }
    fd = model_file.file
    u_id = uuid.uuid4().hex[0:8]
    model_path = os.path.join(
        TMP_DIR,
        f'model-{u_id}.auto'
    )

    with open(model_path, 'w') as f:
        f.write(fd.read().decode('utf8'))
    try:
        if container == 'subprocess':
            pid = run_interpreter(model_path)
            if wait:
                pid.wait()
        else:
            raise ValueError()
    except Exception as e:
        print(e)
        resp['status'] = 404
    return resp


@api.post("/generate/ventities")
async def generate(model_file: UploadFile = File(...)):
    print(f'Generate for request: file=<{model_file.filename}>,' + \
          f' descriptor=<{model_file.file}>')
    resp = {
        'status': 200,
        'message': ''
    }
    fd = model_file.file
    u_id = uuid.uuid4().hex[0:8]
    model_path = os.path.join(
        TMP_DIR,
        f'model-{u_id}.auto'
    )
    tarball_path = os.path.join(
        TMP_DIR,
        f'graph-{u_id}.tar.gz'
    )
    gen_path = os.path.join(
        TMP_DIR,
        f'gen-{u_id}'
    )
    if not os.path.exists(gen_path):
        os.mkdir(gen_path)
    with open(model_path, 'w') as f:
        f.write(fd.read().decode('utf8'))
    try:
        vnodes = model_to_vnodes(model_path)
        for vn in vnodes:
            filepath = f'{vn[0].name}.py'
            with open(filepath, 'w') as fp:
                fp.write(vn[1])
                make_executable(filepath)
        make_tarball(tarball_path, gen_path)
        shutil.rmtree(gen_path)
        print(f'Sending tarball {tarball_path}')
        return FileResponse(tarball_path,
                            filename=os.path.basename(tarball_path),
                            media_type='application/x-tar')
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400,
                            detail=f"VEntity generation error: {e}")

# @api.post("/graph")
# async def generate(model_file: UploadFile = File(...)):
#     print(f'Generate for request: file=<{model_file.filename}>,' + \
#           f' descriptor=<{model_file.file}>')
#     resp = {
#         'status': 200,
#         'message': ''
#     }
#     fd = model_file.file
#     u_id = uuid.uuid4().hex[0:8]
#     model_path = os.path.join(
#         TMP_DIR,
#         f'model-{u_id}.smauto'
#     )
#     tarball_path = os.path.join(
#         TMP_DIR,
#         f'graph-{u_id}.tar.gz'
#     )
#     gen_path = os.path.join(
#         TMP_DIR,
#         f'gen-{u_id}'
#     )
#     if not os.path.exists(gen_path):
#         os.mkdir(gen_path)
#     with open(model_path, 'w') as f:
#         f.write(fd.read().decode('utf8'))
#     try:
#         model = build_model(model_path)
#         # Build entities dictionary in model. Needed for evaluating conditions
#         model.entities_dict = {entity.name: entity for entity in model.entities}
#         for automation in model.automations:
#             automation.build_condition()
#             fpath = generate_automation_graph(
#                 automation,
#                 dest=os.path.join(gen_path, f"automation_{automation.name}.pu")
#             )
#             pu_to_png_transformation(fpath, gen_path)
#
#         make_tarball(tarball_path, gen_path)
#         shutil.rmtree(gen_path)
#         print(f'Sending tarball {tarball_path}')
#         return FileResponse(tarball_path,
#                             filename=os.path.basename(tarball_path),
#                             media_type='application/x-tar')
#     except Exception as e:
#         print(e)
#         resp['status'] = 404
#         return resp
#         if os.path.exists(gen_path):
#             shutil.rmtree(gen_path)


def run_interpreter(model_path: str):
    pid = subprocess.Popen(['smauto', 'interpret', model_path], close_fds=True)
    return pid


def make_tarball(fout, source_dir):
    with tarfile.open(fout, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


def make_executable(path):
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2    # copy R bits to X
    os.chmod(path, mode)
