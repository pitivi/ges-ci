# Create docker containers to build pitivi bundles

## Make sure to have /mnt/bundles mounted:

In `/root/.netrc`:

```
machine ecchi.ca
login pitivibundles@ecchi.ca
password ASK_JEFF!
```

Then in `/etc/fstab`

```
curlftpfs#ecchi.ca /mnt/bundles/ fuse auto,allow_other,uid=1000,gid=1000,umask=0022,_netdev 0 0

```

And:

```
$ sudo mount /etc/fstab
```

Then create the bundler:

Note that on the containers, we mount /home/jenkins/workspace/pitivi_bundling_workspace.x86.64 (which will be the jenkins workspace directory)
onto the container /root/cerbero (`-v /home/jenkins/workspace/pitivi_bundling_workspace.x86.64:/root/cerbero`) so that when I wipe the jenkins
workspace, it wipes /root/cerbero and this way we are sure everything is rebuilt

`64 bits:`

``` bash
$ docker build -t pitivi-bundling-64bits 64bits/ # create the docker image

# Create the container (--privileged is needed to acces /dev/fuse (needed by AppImageKit))
$ docker run --privileged -v  /mnt/bundles:/mnt/bundles -v /home/jenkins/workspace/pitivi_bundling_workspace.x86.64:/root/cerbero -t -i --name=pitivi-bundler-64bits pitivi-bundling-64bits update_bundle
```

`32 bits:`
``` bash
$ docker build -t pitivi-bundling-32bits 32bits/ # create the docker image

# Create the container (--privileged is needed to acces /dev/fuse (needed by AppImageKit))
$ docker run --privileged -v  /mnt/bundles:/mnt/bundles -v /home/jenkins/workspace/pitivi_bundling_workspace.x86:/root/cerbero -t -i --name=pitivi-bundler-32bits pitivi-bundling-32bits update_bundle
```

Then updating the bundles is as simple as doing

`64 bits:`

``` bash
docker start -a pitivi-bundler-64bits

```

`32 bits:`
``` bash
docker start -a pitivi-bundler-32bits
```
