BUILDDIR="tensorflow-notebook"
docker build -t soullessblob/$BUILDDIR:latest -f $BUILDDIR/Dockerfile $BUILDDIR
BUILDDIR="flower-client"
docker build -t soullessblob/$BUILDDIR:latest -f $BUILDDIR/Dockerfile $BUILDDIR
BUILDDIR="flower-server"
docker build -t soullessblob/$BUILDDIR:latest -f $BUILDDIR/Dockerfile $BUILDDIR