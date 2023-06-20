#include <stdio.h>
#include <string.h>
#include <stdlib.h>

char string[100];

char secret[] = "THIS IS A SECRET";

void safe() {
  printf("life is good \n");
}

void evil() {
  printf("you've been pwned %s\n", secret);
}

// I might need this later. ¯\_(ツ)_/¯
// I'm not using it so it shouldn't affect anything.
void lazy() {
  system(string);
}

void food(int magic) {
  printf("THANK YOU!\n");
  if (magic == 0xdeadbeef) {
    strcat(string, "/bin");
  }
}

void feeling_sick(int magic1, int magic2) {
  printf("1m f33ling s1cK...\n");
  if (magic1 == 0xd15ea5e && magic2 == 0x0badf00d) {
    strcat(string, "/echo 'This message will self destruct in 30 seconds...BOOM!'");
  }
}

void vuln(char *string) {
  char buffer[100] = {0};
  void (*fn)() = &safe;
  strcpy(buffer, string); // I don't know any better.
  //printf("buffer is %s\n", buffer);
  //printf("fn is %lx\n", fn);
  if( fn == &safe){
    (*fn)();
  } else {
      evil();
  }
}

int main(int argc, char** argv) {
  string[0] = 0;

  //if the program doesn't work at first, uncomment this line and make sure
  //printf("evil: %lx \n", (void *)&evil);
  printf("This program is running normally, going to process arguments now\n\n");
  if (argc > 1) {
    vuln(argv[1]);
  } else {
    printf("usage: %s <string argument\n", argv[0]);
  }
  return 0;
}
