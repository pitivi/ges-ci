FROM fedora:23
# That list will need updating...
RUN dnf -y install xdg-app git dnf-plugins-core json-glib-devel
RUN dnf groupinstall -y "C Development Tools and Libraries"
RUN dnf -y builddep xdg-app
Upp add-remote --user gnome-sdk http://sdk.gnome.org/repo/  N mkdir /root/devel
RUN cd /root/devel/ && git clone https://github.com/pitivi/pitivi-bundler.git
RUN cd /root/devel/pitivi-bundler && git pull --rebase
RUN cd /root/devel/ && git clone git://anongit.freedesktop.org/xdg-app/xdg-app && cd xdg-app ./autogen.sh --prefix=/usr && make && make install
RUN echo "#!/bin/sh" > /usr/bin/update_bundle
RUN echo "cd /root/devel/pitivi-bundler/ && git fetch && git reset --hard origin/master && /root/devel/pitivi-bundler/xdg-app/build.sh" >> /usr/bin/update_bundle
RUN chmod +x /usr/bin/update_bundle
run curl http://sdk.gnome.org/keys/gnome-sdk.gpg > /usr/share/ostree/trusted.gpg.d/gnome-sdk.gpg
RUN xdg-app add-remote --no-gpg-verify --user gnome-sdk http://sdk.gnome.org/repo/
RUN xdg-app install-runtime --user gnome-sdk org.gnome.Platform 3.18
RUN xdg-app install-runtime --user gnome-sdk org.gnome.Sdk 3.18
CMD update_bundle
