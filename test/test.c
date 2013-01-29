#include "test.h"

#define nbytes(len) len
#define FOO(nbytes) (nbytes)

#define logError(fmt, ...)       \
do {                             \
    printf(fmt, ## __VA_ARGS__); \
    exit(1);                     \
} while(0);

#pragma pack(4)
#pragma GCC diagnostic warning "-Wuninitialized"

unsigned int func0();
unsigned int func00(void);
unsigned long (func1)();
unsigned long (func11)(void);
int func2(int a, int b);
int (*funcPtr1)(int a, int b);
int (*funcPtrArr1[11])(int a, int b);
int (*funcPtrFunc(int a, int b))(int c, int d);
int* (*(*funcPtrArr[10])(int* a, int b))(int* c, int d);
int* (*(**funcPtrArrPtr)(int* a, int b))(int* c, int d);
int* funcf(int (*callback)(int, int), int (*callbackArr[10])(int, int));

typedef unsigned int uint32;
typedef uint32 myFunc(int, uint32);
typedef long int (*funcPtr)(int, int);
typedef myFunc *myFuncPtr;

struct bar
{
    myFunc *add;
    myFunc *sub;
    myFunc *mul;
    uint32 (*fn)(uint32, uint32);
    int (*fnArr[10])(int, int);
    const char *(*ff[2])(const char*, int *);
} bar_1, bar_2;

typedef union
{
    struct {
        unsigned a : 8;
        unsigned b : 8;
        unsigned c : 8;
        unsigned d : 8;
    } four_bytes;
    unsigned int abcd;
} abcd_t;

enum eColor {RED=0, BLUE, YELLOW} c1, c2;
typedef enum{
    CAT = 0,
    DOG = 1,
    LION,
    DRAGON,
} ANIMAL;

struct position
{
    short x;
    short y;
} pos1 = {.x=CAT, .y=DOG};

int (addition)(int a, int b);

extern int addition(int a, int b);

int addition(int a, int b) {return a + b;}
int subtraction(int a, int b) {return a - b;}
int multiplication(int a, int b) {return a * b;}
uint32 test_func(int a) {return (uint32)a;}

int rec_func(int val)
{
    if(val <= 0)
    {
        return val;
    }
    else
    {
        return rec_func(val - 1);
    }
}

#if 0
int (*returnFuncPtr(void))(int, int) {return addition;}
#endif
void execFunc(int (*callback)(int, int), int a, int b) {printf("%d\n", (*callback)(a, b));}
#if 0
extern void (*function(int, void (*)(int)))(int);
#endif
#if 0
extern int func1(int), func2(double); double func3(int), x;
#endif

static int foo = LION;
static int bar[10];

int main(void)
{
    myFunc *add = &addition;
    myFuncPtr sub = &subtraction;
    int (*mul)(int,int) = multiplication;
    int (*funcArr[3])(int, int) = {&addition, &subtraction, &multiplication};
    ANIMAL animal = CAT;
    uint32 val;
    void* ptr = (void*)&val;
    struct position pos = {.x=3, .y=4};
    enum eColor c = RED;

    int x = add(3,2), y = (*sub)(5,foo), z = mul(addition(3,4), bar[sub(5,3)]);

    *(uint32*)ptr = (uint32)animal;

    pos = *(struct position*)&val;

    printf("hello"
            "world\n");
    printf("hello" \
            "world\n");
    printf("%c%c\n", '\x30','\x39');
    execFunc(add, 1, 2);
    execFunc(sub, 1, 2);
    execFunc(mul, 1, FOO(2));
    //execFunc(returnFuncPtr(), 1, 2);

    if(1)
        if(0)
            printf("xy\n");
        else
            printf("x desu\n");

    if(x < 0)
    {
        printf("x < 0\n");
    }
    else if(x < 10)
    {
        printf("0 <= x < 10\n");
    }
    else if(x < 20)
    {
        printf("10 <= x < 20\n");
    }
    else if(x < 30)
    {
        logError("20 <= x < 30\n");
    }
    else
    {
        logError("x >= 30 (%d, %d, %d)\n", x, (int)y, &z);
    }

    for(x = 0; x < y; x++)
    {
        int i;
        execFunc(add, 1, 2);
    }

    while(0)
    {
        int aa;
        if(0)
        {
            int xx = 0;
            for(xx = 0; xx < 100; xx++)
            {
                int bb;
            }
        }
        else if(1)
        {
            int yy;
            switch(2)
            {
                case 2:
                    break;
                default:
                    break;
            }
        }
        else
        {
            int zz;
            do
            {
                printf("");
            }
            while(0);
        }
        printf("hello world\n");
        continue;
    }

    switch(x)
    {
        case 1: printf("1\n"); break;
        case 2: printf("2\n"); break;
        default: printf("other\n"); break;
    }

    return 0;
}
