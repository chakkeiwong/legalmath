FROM haskell:9.2.8

# Before we do anything, properly symlink the Haskell compiler
RUN ln -s /opt/ghc/9.2.8/bin/ghc /opt/ghc/9.2.8/bin/ghc-9.2

# Prepare the directory to build in
RUN mkdir /tmp/eflint-project
WORKDIR /tmp/eflint-project

# Prepare cabal
RUN cabal update

# Install eFLINT
COPY . .
RUN cabal install

# Save the executables to a PATH-location, then delete the build cache
RUN cp /root/.cabal/bin/eflint-server /usr/bin/eflint-server \
 && cp /root/.cabal/bin/eflint-repl /usr/bin/eflint-repl \
 && rm -rf /tmp/eflint-project

# Prepare the start script
RUN printf '#!/bin/bash\n\nwhat="/usr/bin/eflint-repl"\nargs=()\nif [[ "$#" -ge 1 ]]; then\n    args=($@)\n    args=(${args[@]:1})\n    if [[ "$1" == "server" ]]; then\n        what="/usr/bin/eflint-server"\n    elif [[ "$1" != "repl" ]]; then\n        2>&1 echo "Unknown command \\"$1\\""\n    fi\nfi\n\n"$what" ${args[@]}\n\n' > /start.sh \
 && chmod +x /start.sh

# Set the entrypoint and we are done
WORKDIR /
ENTRYPOINT [ "/start.sh" ]

